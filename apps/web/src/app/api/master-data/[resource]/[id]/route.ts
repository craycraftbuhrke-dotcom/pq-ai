import { proxyMasterDataRequest } from "@/lib/server-api-proxy";

type Context = { params: Promise<{ resource: string; id: string }> };

export async function GET(request: Request, context: Context) {
  const { resource, id } = await context.params;
  return proxyMasterDataRequest(request, resource, id);
}

export async function PATCH(request: Request, context: Context) {
  const { resource, id } = await context.params;
  return proxyMasterDataRequest(request, resource, id);
}
