/**
 * services/tasks/McpDynamicTaskStore.ts
 *
 * Dynamic TaskStore & TaskStorePmSurface implementation that delegates
 * task creation, closing, listing, and sprint/member queries to the central
 * mcp-gateway (port 8005). Supports both Jira and Taiga dynamically per tenant.
 */
import type { TaskStore, Task, TaskInput, TaskChanges, TaskStorePmSurface } from './TaskStore.js';
import { McpTaskClient } from './McpTaskClient.js';
import { IdentityServiceClient } from '../../integrations/identity/IdentityServiceClient.js';

export interface McpDynamicTaskStoreOptions {
  mcpClient?: McpTaskClient;
  identityClient?: IdentityServiceClient;
  fallbackStore?: TaskStore;
  defaultProjectSlug?: string;
}

export class McpDynamicTaskStore implements TaskStore, TaskStorePmSurface {
  private mcpClient: McpTaskClient;
  private identityClient: IdentityServiceClient;
  private fallbackStore?: TaskStore;
  private defaultProjectSlug?: string;

  constructor(opts: McpDynamicTaskStoreOptions = {}) {
    this.mcpClient = opts.mcpClient || new McpTaskClient();
    this.identityClient = opts.identityClient || new IdentityServiceClient();
    this.fallbackStore = opts.fallbackStore;
    this.defaultProjectSlug = opts.defaultProjectSlug;
  }

  async create(orgId: string, input: TaskInput): Promise<Task> {
    const authContext: Record<string, unknown> = { org_id: orgId };

    // Attempt Jira create_issue first
    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_create_issue',
      {
        summary: input.title,
        description: input.description || '',
        issue_type: 'Task',
      },
      authContext
    );

    if (jiraRes.status === 'success') {
      const resultData = jiraRes.result as Record<string, unknown> | undefined;
      const key = (resultData?.key as string) || (resultData?.id as string) || String(Date.now());
      return {
        id: key,
        orgId,
        title: input.title,
        description: input.description,
        assignee: input.assignee,
        status: 'open',
        createdBy: input.createdBy,
        createdAt: Date.now(),
        closedAt: null,
        sourceChannelId: input.sourceChannelId,
      };
    }

    // Attempt Taiga create_task
    const taigaRes = await this.mcpClient.execute(
      'taiga',
      'taiga_create_task',
      {
        subject: input.title,
        description: input.description || '',
      },
      authContext
    );

    if (taigaRes.status === 'success') {
      const resultData = taigaRes.result as Record<string, unknown> | undefined;
      const id = String(resultData?.id || resultData?.ref || Date.now());
      return {
        id,
        orgId,
        title: input.title,
        description: input.description,
        assignee: input.assignee,
        status: 'open',
        createdBy: input.createdBy,
        createdAt: Date.now(),
        closedAt: null,
        sourceChannelId: input.sourceChannelId,
      };
    }

    if (this.fallbackStore) {
      return this.fallbackStore.create(orgId, input);
    }

    throw new Error(jiraRes.message || taigaRes.message || 'Failed to create task via PM tools');
  }

  async close(orgId: string, taskIdOrTitle: string): Promise<Task | null> {
    const authContext: Record<string, unknown> = { org_id: orgId };

    // Try Jira transition
    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_transition_issue',
      {
        issue_key: taskIdOrTitle,
        status: 'Done',
      },
      authContext
    );

    if (jiraRes.status === 'success') {
      return {
        id: taskIdOrTitle,
        orgId,
        title: taskIdOrTitle,
        status: 'closed',
        createdBy: 'voice-assistant',
        createdAt: Date.now() - 60000,
        closedAt: Date.now(),
        sourceChannelId: '',
      };
    }

    // Try Taiga task close
    const taigaRes = await this.mcpClient.execute(
      'taiga',
      'taiga_update_task',
      {
        task_id: taskIdOrTitle,
        status: 'closed',
      },
      authContext
    );

    if (taigaRes.status === 'success') {
      return {
        id: taskIdOrTitle,
        orgId,
        title: taskIdOrTitle,
        status: 'closed',
        createdBy: 'voice-assistant',
        createdAt: Date.now() - 60000,
        closedAt: Date.now(),
        sourceChannelId: '',
      };
    }

    if (this.fallbackStore) {
      return this.fallbackStore.close(orgId, taskIdOrTitle);
    }

    return null;
  }

  async update(orgId: string, taskIdOrTitle: string, changes: TaskChanges): Promise<Task | null> {
    const authContext: Record<string, unknown> = { org_id: orgId };

    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_update_issue',
      {
        issue_key: taskIdOrTitle,
        summary: changes.title,
        description: changes.description,
      },
      authContext
    );

    if (jiraRes.status === 'success') {
      return {
        id: taskIdOrTitle,
        orgId,
        title: changes.title || taskIdOrTitle,
        description: changes.description,
        assignee: changes.assignee,
        status: 'open',
        createdBy: 'voice-assistant',
        createdAt: Date.now() - 60000,
        closedAt: null,
        sourceChannelId: '',
      };
    }

    if (this.fallbackStore) {
      return this.fallbackStore.update(orgId, taskIdOrTitle, changes);
    }

    return null;
  }

  async list(orgId: string, status?: 'open' | 'closed'): Promise<Task[]> {
    const authContext: Record<string, unknown> = { org_id: orgId };

    // Try Jira list issues
    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_list_issues',
      { status: status || 'all' },
      authContext
    );

    if (jiraRes.status === 'success' && Array.isArray(jiraRes.result)) {
      return (jiraRes.result as Array<Record<string, unknown>>).map((item) => ({
        id: String(item.key || item.id),
        orgId,
        title: String(item.summary || item.title || item.key),
        description: item.description ? String(item.description) : undefined,
        status: item.status === 'Done' || item.status === 'Closed' ? 'closed' : 'open',
        createdBy: String(item.creator || 'jira'),
        createdAt: Date.now(),
        closedAt: null,
        sourceChannelId: '',
      }));
    }

    // Try Taiga list tasks
    const taigaRes = await this.mcpClient.execute(
      'taiga',
      'taiga_list_tasks',
      { status: status || 'all' },
      authContext
    );

    if (taigaRes.status === 'success' && Array.isArray(taigaRes.result)) {
      return (taigaRes.result as Array<Record<string, unknown>>).map((item) => ({
        id: String(item.id || item.ref),
        orgId,
        title: String(item.subject || item.title),
        description: item.description ? String(item.description) : undefined,
        status: item.is_closed ? 'closed' : 'open',
        createdBy: String(item.owner || 'taiga'),
        createdAt: Date.now(),
        closedAt: item.is_closed ? Date.now() : null,
        sourceChannelId: '',
      }));
    }

    if (this.fallbackStore) {
      return this.fallbackStore.list(orgId, status);
    }

    return [];
  }

  async get(orgId: string, id: string): Promise<Task | null> {
    const tasks = await this.list(orgId);
    return tasks.find((t) => t.id === id) || null;
  }

  // ── PM Surface Implementation ──────────────────────────────────────────────

  async getProjectLabel(orgId?: string): Promise<string> {
    return this.defaultProjectSlug || (orgId ? `Org ${orgId}` : 'Default Project');
  }

  async getActiveSprint(orgId?: string): Promise<Record<string, unknown> | null> {
    const authContext: Record<string, unknown> = orgId ? { org_id: orgId } : {};

    // Try Taiga sprint
    const taigaRes = await this.mcpClient.execute(
      'taiga',
      'taiga_get_active_sprint',
      {},
      authContext
    );
    if (taigaRes.status === 'success' && taigaRes.result) {
      return taigaRes.result as Record<string, unknown>;
    }

    // Try Jira sprint
    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_get_active_sprint',
      {},
      authContext
    );
    if (jiraRes.status === 'success' && jiraRes.result) {
      return jiraRes.result as Record<string, unknown>;
    }

    return null;
  }

  async listMembers(orgId?: string): Promise<Array<Record<string, string | number>>> {
    const authContext: Record<string, unknown> = orgId ? { org_id: orgId } : {};

    // Try Taiga members
    const taigaRes = await this.mcpClient.execute(
      'taiga',
      'taiga_list_members',
      {},
      authContext
    );
    if (taigaRes.status === 'success' && Array.isArray(taigaRes.result)) {
      return taigaRes.result as Array<Record<string, string | number>>;
    }

    // Try Jira assignable users / members
    const jiraRes = await this.mcpClient.execute(
      'jira',
      'jira_list_users',
      {},
      authContext
    );
    if (jiraRes.status === 'success' && Array.isArray(jiraRes.result)) {
      return (jiraRes.result as Array<Record<string, unknown>>).map((u, idx) => ({
        id: idx + 1,
        username: String(u.displayName || u.name || u.accountId || 'user'),
        fullName: String(u.displayName || u.name || 'User'),
        role: 'Member',
      }));
    }

    return [];
  }
}
