import type { MeetingLauncher } from '../SchedulerService.js';
import type { ScheduledMeeting } from '../types.js';
import type { CredentialsStore } from '../../store/CredentialsStore.js';
import { getDiscordClient } from '../../discord/DiscordBotClient.js';
import { startDiscordMeeting } from '../../discord/DiscordMeetingManager.js';

/** Wakes the bot up at the scheduled time and joins the configured voice channel. */
export class DiscordLauncher implements MeetingLauncher {
  readonly provider = 'discord';

  constructor(private readonly credentialsStore: CredentialsStore) {}

  async launch(schedule: ScheduledMeeting): Promise<void> {
    // ScheduledMeeting already carries its own orgId (SchedulerService runs
    // across every org's schedules in one background loop, not per-request
    // — see SchedulerService's tick(), which calls listAllEnabled() across
    // all orgs). The credentials store itself was already properly
    // org-scoped; this just needed to actually pass the schedule's real
    // org instead of a hardcoded placeholder.
    const creds = await this.credentialsStore.get(schedule.orgId, 'discord');
    const botToken = creds?.bot_token || creds?.botToken || creds?.token || process.env.DISCORD_BOT_TOKEN || process.env.DISCORD_TOKEN;
    if (!botToken) {
      throw new Error(`Discord is not configured for organization "${schedule.orgId}" — configure its bot token in the organization Tools page or set DISCORD_BOT_TOKEN.`);
    }
    const client = await getDiscordClient(botToken);
    await startDiscordMeeting(client, schedule.guildId, schedule.channelId, schedule.durationMs);
  }
}
