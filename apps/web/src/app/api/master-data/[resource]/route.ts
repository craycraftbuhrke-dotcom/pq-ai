import { proxyMasterDataRequest } from "@/lib/server-api-proxy";

type Context = { params: Promise<{ resource: string }> };

export async function GET(request: Request, context: Context) {
  const { resource } = await context.params;
  return proxyMasterDataRequest(request, resource);
}

export async function POST(request: Request, context: Context) {
  const { resource } = await context.params;
  return proxyMasterDataRequest(request, resource);
}
