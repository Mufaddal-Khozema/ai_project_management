import type { FastifyInstance, FastifyRequest } from 'fastify';
import type { CredentialsStore } from '../store/CredentialsStore.js';
import { getDiscordClient, listGuildVoiceChannels } from '../discord/DiscordBotClient.js';
import { startDiscordMeeting, stopDiscordMeeting, getDiscordMeeting, listActiveDiscordMeetings } from '../discord/DiscordMeetingManager.js';
import { requireAuth } from '../../auth/requireAuth.js';

export default function registerDiscordMeetingRoutes(
  fastify: FastifyInstance,
  deps: { credentialsStore: CredentialsStore }
): void {
  const { credentialsStore } = deps;

  async function getBotToken(orgId: string): Promise<string> {
    const creds = await credentialsStore.get(orgId, 'discord');
    const botToken = creds?.bot_token || creds?.botToken || creds?.token || process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_TOKEN;
    if (!botToken) {
      throw new Error(
        `Discord is not configured for organization "${orgId}" — configure its bot token in the organization Tools page or set DISCORD_BOT_TOKEN environment variable.`
      );
    }
    return botToken;
  }

  // ── List servers + voice channels the bot can join ───────────────────────────
  fastify.get('/integrations/discord/guilds', { preHandler: requireAuth }, async (req: FastifyRequest, reply) => {
    try {
      const botToken = await getBotToken(req.orgId!);
      return await listGuildVoiceChannels(botToken);
    } catch (err) {
      return reply.code(400).send({ error: err instanceof Error ? err.message : 'Failed to list Discord servers' });
    }
  });

  // ── Start a standup in a specific server + voice channel ─────────────────────
  fastify.post('/integrations/discord/meetings/start', { preHandler: requireAuth }, async (req: FastifyRequest, reply) => {
    const body = (req.body ?? {}) as any;
    const guildId = body.guildId || body.guild_id;
    const channelId = body.channelId || body.channel_id || body.voice_channel_id;
    const textChannelId = body.textChannelId || body.text_channel_id;
    const durationMs = body.durationMs || body.duration_ms;
    const projectSlug = body.projectSlug || body.project_slug;
    if (!guildId || !channelId) return reply.code(400).send({ error: 'guildId and channelId are required' });

    try {
      const botToken = await getBotToken(req.orgId!);
      const client = await getDiscordClient(botToken);
      await startDiscordMeeting(client, guildId, channelId, durationMs, textChannelId, projectSlug);
      return { started: true, guildId, channelId };
    } catch (err) {
      return reply.code(400).send({ error: err instanceof Error ? err.message : 'Failed to start the meeting' });
    }
  });

  // ── Stop the active standup in a server ──────────────────────────────────────
  fastify.post('/integrations/discord/meetings/stop', { preHandler: requireAuth }, async (req: FastifyRequest, reply) => {
    const body = (req.body ?? {}) as any;
    const guildId = body.guildId || body.guild_id;
    if (!guildId) return reply.code(400).send({ error: 'guildId is required' });
    await stopDiscordMeeting(guildId);
    return { stopped: true, guildId };
  });

  // ── Which servers currently have a meeting running (for UI auto-discovery) ──
  fastify.get('/integrations/discord/meetings/active', { preHandler: requireAuth }, async () => {
    // Same caveat as stopDiscordMeeting above — this returns active
    // meetings across ALL orgs' guilds, not filtered to the caller's own
    // org, since that mapping doesn't exist in DiscordMeetingManager yet.
    return { guildIds: listActiveDiscordMeetings() };
  });

  // ── Poll current meeting state (participants, phase, standup data, transcript) ─
  fastify.get('/integrations/discord/meetings/:guildId/status', { preHandler: requireAuth }, async (req: FastifyRequest, reply) => {
    const { guildId } = req.params as { guildId: string };
    const room = getDiscordMeeting(guildId);
    if (!room) return reply.code(404).send({ error: 'No active meeting in that server' });
    return room.getState();
  });
}
