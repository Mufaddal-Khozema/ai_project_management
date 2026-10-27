/**
 * McpTaskClient.ts — Client forwarding voice assistant tool calls to the central mcp-gateway.
 */
export interface McpExecutionResult {
  status: 'success' | 'error' | 'forbidden';
  error_code?: string;
  message?: string;
  tool_name?: string;
  category?: string;
  result?: unknown;
  did_you_mean?: string[];
  supported_tools?: string[];
}

export class McpTaskClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = (baseUrl || process.env.MCP_GATEWAY_URL || 'http://mcp-gateway:8005').replace(/\/+$/, '');
  }

  async execute(
    toolType: string,
    toolName: string,
    parameters: Record<string, unknown>,
    authContext: Record<string, unknown>
  ): Promise<McpExecutionResult> {
    try {
      const resp = await fetch(`${this.baseUrl}/tools/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_type: toolType,
          tool_name: toolName,
          parameters,
          auth_context: authContext,
        }),
      });

      if (!resp.ok && resp.status !== 403 && resp.status !== 400) {
        return {
          status: 'error',
          error_code: `HTTP_${resp.status}`,
          message: `MCP Gateway responded with status ${resp.status}`,
        };
      }

      const data = (await resp.json()) as McpExecutionResult;
      return data;
    } catch (err) {
      return {
        status: 'error',
        error_code: 'CONNECTION_FAILED',
        message: err instanceof Error ? err.message : String(err),
      };
    }
  }

  async search(query = '', category?: string): Promise<Record<string, unknown>> {
    try {
      const resp = await fetch(`${this.baseUrl}/tools/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, category }),
      });
      return (await resp.json()) as Record<string, unknown>;
    } catch (err) {
      return { status: 'error', message: String(err) };
    }
  }
}
