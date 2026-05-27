/**
 * 类型 stub:真实文件由 `npx openapi-typescript` 从 openapi.json 生成。
 * 这里保留一个最小有效 schema,让 client.ts 在未生成时也能 typecheck。
 *
 * 真生成命令(同 lib/api/README.md):
 *   npx openapi-typescript lib/api/openapi.json -o lib/api/schema.d.ts
 */

export interface paths {
  "/healthz": {
    get: { responses: { 200: { content: { "application/json": { status: string; version: string } } } } };
  };
  "/v1/trails": {
    post: {
      requestBody: { content: { "application/json": { name: string; location_name?: string; gpx_uri?: string } } };
      responses: { 201: { content: { "application/json": Trail } } };
    };
  };
  "/v1/trails/{trail_id}": {
    get: {
      parameters: { path: { trail_id: string } };
      responses: { 200: { content: { "application/json": Trail } }; 404: { content: { "application/json": { detail: string } } } };
    };
  };
}

export interface Trail {
  id: string;
  user_id: string;
  name: string;
  location_name?: string | null;
  gpx_uri?: string | null;
  travelogue_md?: string | null;
  next_trip_plan?: Record<string, unknown> | null;
  photo_count: number;
  state_summary: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type components = unknown;
export type operations = unknown;
