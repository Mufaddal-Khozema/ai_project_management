import { describe, it, expect, vi, beforeEach } from 'vitest';
import { McpDynamicTaskStore } from '../McpDynamicTaskStore.js';
import type { McpTaskClient } from '../McpTaskClient.js';
import type { TaskStore, Task } from '../TaskStore.js';

describe('McpDynamicTaskStore', () => {
  let mockMcpClient: Partial<McpTaskClient>;
  let mockFallbackStore: Partial<TaskStore>;

  beforeEach(() => {
    vi.restoreAllMocks();
    mockMcpClient = {
      execute: vi.fn(),
      search: vi.fn(),
    };
    mockFallbackStore = {
      create: vi.fn(),
      close: vi.fn(),
      update: vi.fn(),
      list: vi.fn(),
      get: vi.fn(),
    };
  });

  describe('create()', () => {
    it('creates an issue in Jira when Jira tool succeeds', async () => {
      vi.mocked(mockMcpClient.execute!).mockResolvedValueOnce({
        status: 'success',
        result: { key: 'SCRUM-42', id: '10042' },
      });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const task = await store.create('org-uuid-1', {
        title: 'Fix authentication bug',
        description: 'Users cannot log in via OAuth',
        createdBy: 'Alice',
        sourceChannelId: 'channel-123',
      });

      expect(task.id).toBe('SCRUM-42');
      expect(task.orgId).toBe('org-uuid-1');
      expect(task.title).toBe('Fix authentication bug');
      expect(task.status).toBe('open');
      expect(mockMcpClient.execute).toHaveBeenCalledWith(
        'jira',
        'jira_create_issue',
        {
          summary: 'Fix authentication bug',
          description: 'Users cannot log in via OAuth',
          issue_type: 'Task',
        },
        { org_id: 'org-uuid-1' }
      );
    });

    it('falls back to Taiga when Jira tool fails', async () => {
      vi.mocked(mockMcpClient.execute!)
        .mockResolvedValueOnce({
          status: 'error',
          message: 'Jira not connected',
        })
        .mockResolvedValueOnce({
          status: 'success',
          result: { id: 101, ref: 12 },
        });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const task = await store.create('org-uuid-2', {
        title: 'Add Taiga unit tests',
        createdBy: 'Bob',
        sourceChannelId: 'channel-456',
      });

      expect(task.id).toBe('101');
      expect(task.orgId).toBe('org-uuid-2');
      expect(task.title).toBe('Add Taiga unit tests');
      expect(mockMcpClient.execute).toHaveBeenCalledWith(
        'taiga',
        'taiga_create_task',
        {
          subject: 'Add Taiga unit tests',
          description: '',
        },
        { org_id: 'org-uuid-2' }
      );
    });

    it('delegates to fallbackStore when both Jira and Taiga fail', async () => {
      vi.mocked(mockMcpClient.execute!)
        .mockResolvedValueOnce({ status: 'error', message: 'No Jira' })
        .mockResolvedValueOnce({ status: 'error', message: 'No Taiga' });

      const fallbackTask: Task = {
        id: 'mongo-id-1',
        orgId: 'org-uuid-3',
        title: 'Offline task',
        status: 'open',
        createdBy: 'Charlie',
        createdAt: Date.now(),
        closedAt: null,
        sourceChannelId: 'channel-789',
      };
      vi.mocked(mockFallbackStore.create!).mockResolvedValueOnce(fallbackTask);

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
        fallbackStore: mockFallbackStore as TaskStore,
      });

      const result = await store.create('org-uuid-3', {
        title: 'Offline task',
        createdBy: 'Charlie',
        sourceChannelId: 'channel-789',
      });

      expect(result).toEqual(fallbackTask);
      expect(mockFallbackStore.create).toHaveBeenCalledWith('org-uuid-3', {
        title: 'Offline task',
        createdBy: 'Charlie',
        sourceChannelId: 'channel-789',
      });
    });
  });

  describe('list()', () => {
    it('returns Jira issues mapped to Tasks', async () => {
      vi.mocked(mockMcpClient.execute!).mockResolvedValueOnce({
        status: 'success',
        result: [
          { key: 'SCRUM-1', summary: 'Issue 1', status: 'In Progress', creator: 'Dev' },
          { key: 'SCRUM-2', summary: 'Issue 2', status: 'Done', creator: 'Dev' },
        ],
      });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const tasks = await store.list('org-uuid-1');
      expect(tasks).toHaveLength(2);
      expect(tasks[0].id).toBe('SCRUM-1');
      expect(tasks[0].status).toBe('open');
      expect(tasks[1].id).toBe('SCRUM-2');
      expect(tasks[1].status).toBe('closed');
    });
  });

  describe('close()', () => {
    it('transitions Jira issues to Done', async () => {
      vi.mocked(mockMcpClient.execute!).mockResolvedValueOnce({
        status: 'success',
        result: { status: 'Done' },
      });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const closed = await store.close('org-uuid-1', 'SCRUM-42');
      expect(closed).not.toBeNull();
      expect(closed?.id).toBe('SCRUM-42');
      expect(closed?.status).toBe('closed');
      expect(mockMcpClient.execute).toHaveBeenCalledWith(
        'jira',
        'jira_transition_issue',
        { issue_key: 'SCRUM-42', status: 'Done' },
        { org_id: 'org-uuid-1' }
      );
    });
  });

  describe('PM Surface (listMembers & getActiveSprint)', () => {
    it('lists members from Taiga or Jira', async () => {
      vi.mocked(mockMcpClient.execute!).mockResolvedValueOnce({
        status: 'success',
        result: [{ id: 1, username: 'alice', fullName: 'Alice' }],
      });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const members = await store.listMembers('org-uuid-1');
      expect(members).toHaveLength(1);
      expect(members[0].username).toBe('alice');
    });

    it('retrieves active sprint information', async () => {
      vi.mocked(mockMcpClient.execute!).mockResolvedValueOnce({
        status: 'success',
        result: { name: 'Sprint 1', id: 456, state: 'active' },
      });

      const store = new McpDynamicTaskStore({
        mcpClient: mockMcpClient as McpTaskClient,
      });

      const sprint = await store.getActiveSprint('org-uuid-1');
      expect(sprint).not.toBeNull();
      expect(sprint?.name).toBe('Sprint 1');
    });
  });
});
