import type { FastifyInstance } from 'fastify';
import type { Client } from 'discord.js';
import { MongoAmbientChannelStore } from './store/MongoAmbientChannelStore.js';
import { AmbientPresenceManager } from './AmbientPresenceManager.js';
import registerAmbientChannelRoutes from './routes/ambientChannels.js';
import registerAmbientTaskRoutes from './routes/ambientTasks.js';

import { MongoTaskStore } from '../../../services/tasks/MongoTaskStore.js';
import {
  AMBIENT_TASK_TOOLS,
  handleAmbientFunctionCall,
} from './taskActions.js';

// ── Kafka integration ────────────────────────────────────────────────────────
import { getOrCreateProducer } from '../../../kafka/setupKafka.js';
import { KafkaTaskStore } from '../../../tasks/KafkaTaskStore.js';
import { MeetingEventPublisher } from '../../../meeting/MeetingEventPublisher.js';
import { v4 as uuidv4 } from 'uuid';

// ── Taiga integration (direct PM-platform access) ───────────────────────────
import { config, isTaigaConfigured } from '../../../config/index.js';
import { TaigaTaskStore } from '../../../services/tasks/TaigaTaskStore.js';
import { McpDynamicTaskStore } from '../../../services/tasks/McpDynamicTaskStore.js';

export async function setupAmbientAssistant(
  fastify: FastifyInstance,
  deps: { discordClient: Client; orgId?: string }
): Promise<void> {
  const orgId = deps.orgId || '';
  const channelStore = new MongoAmbientChannelStore();

  // ── Kafka setup ───────────────────────────────────────────────────────────
  const kafkaProducer = await getOrCreateProducer();

  // ── Meeting event publisher ───────────────────────────────────────────────
  const meetingPublisher = kafkaProducer
    ? new MeetingEventPublisher(kafkaProducer, {
        channelId: 'ambient',
        channelName: 'ambient',
        orgId,
      })
    : null;

  // ── Task store ────────────────────────────────────────────────────────────
  const taigaConfigured = isTaigaConfigured();
  const baseStore = taigaConfigured
    ? new TaigaTaskStore({
        url: config.taiga.url,
        username: config.taiga.username,
        password: config.taiga.password,
        projectSlug: config.taiga.projectSlug,
      })
    : kafkaProducer
      ? new KafkaTaskStore(
          kafkaProducer,
          orgId || 'default',
          () => meetingPublisher?.getMeetingId()
        )
      : new MongoTaskStore();

  const useMcpGateway = process.env.USE_MCP_GATEWAY !== 'false';
  const taskStore = useMcpGateway
    ? new McpDynamicTaskStore({ fallbackStore: baseStore })
    : baseStore;

  // ── Task action handler ───────────────────────────────────────────────────
  const originalHandle = (call: any, ctx: any) => {
    const effectiveOrgId = ctx.orgId || orgId || 'default';
    return handleAmbientFunctionCall(
      taskStore,
      effectiveOrgId,
      ctx.channelId,
      ctx.speakerName,
      call
    );
  };

  const instrumentedHandle = async (call: any, ctx: any) => {
    const result = await originalHandle(call, ctx);

    if (meetingPublisher && 'task' in result && result.task) {
      if (call.name === 'create_task') {
        meetingPublisher.onTaskCreated(result.task.id);
      }

      if (call.name === 'close_task') {
        meetingPublisher.onTaskClosed(result.task.id);
      }
    }

    return result;
  };

  // ── Ambient presence manager ──────────────────────────────────────────────
  const presence = new AmbientPresenceManager(
    deps.discordClient,
    channelStore,
    {
      declarations: AMBIENT_TASK_TOOLS,

      handle: instrumentedHandle,

      // ── Transcript → Kafka ──────────────────────────────────────────────
      onTranscript: (
        role: 'user' | 'assistant',
        text: string,
        speakerName?: string,
        channelOrgId?: string
      ) => {
        meetingPublisher?.onTranscript(role, text, speakerName, channelOrgId);
      },

      // ── Session started → meeting.started ───────────────────────────────
      onSessionStarted: (
        channelId: string,
        channelName: string,
        participants: Array<{ id: string; name: string }>,
        channelOrgId?: string
      ) => {
        if (!meetingPublisher) {
          return;
        }

        const effectiveOrgId = channelOrgId || orgId || 'default';
        meetingPublisher.setSessionContext(channelId, channelName, effectiveOrgId);

        const meetingId = uuidv4();
        meetingPublisher.onMeetingStarted(
          meetingId,
          participants,
          effectiveOrgId
        );
      },

      // ── Session ended → meeting.ended ──────────────────────────────────
      onSessionEnded: (
        participants: Array<{ id: string; name: string }>,
        channelOrgId?: string
      ) => {
        meetingPublisher?.onMeetingEnded(participants, channelOrgId);
      },
    }
  );

  // ── Start Discord/Gemini presence ─────────────────────────────────────────
  await presence.start();

  // ── HTTP routes ────────────────────────────────────────────────────────────
  registerAmbientChannelRoutes(fastify, {
    store: channelStore,
    presence,
  });

  registerAmbientTaskRoutes(fastify, {
    store: taskStore,
  });

  // ── Startup logging ────────────────────────────────────────────────────────
  const storeMode = useMcpGateway
    ? 'McpDynamicTaskStore (dynamic Jira & Taiga via mcp-gateway)'
    : taigaConfigured
      ? 'TaigaTaskStore (direct Taiga access)'
      : kafkaProducer
        ? 'KafkaTaskStore (MongoDB + Kafka events)'
        : 'MongoTaskStore (MongoDB only)';
  fastify.log.info(
    kafkaProducer
      ? `[integrations] ambient assistant enabled (presence + Gemini + task actions, store=${storeMode}, Kafka events on)`
      : `[integrations] ambient assistant enabled (presence + Gemini + task actions, store=${storeMode}, Kafka disabled)`
  );
}