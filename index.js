export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Client IP
    const clientIP = request.headers.get('cf-connecting-ip') || 'unknown';

    // Cloudflare edge info
    const cfInfo = request.cf || {};
    const cloudflareInfo = {
      region: cfInfo.region || 'unknown',
      city: cfInfo.city || 'unknown',
      colo: cfInfo.colo || 'unknown',
      country: cfInfo.country || 'unknown',
    };

    // Server / website info
    const serverInfo = {
      protocol: url.protocol,
      hostname: url.hostname,
      pathname: url.pathname,
      fullURL: url.href,
      origin: url.origin,
      port: url.port || 'default',
    };

    // Fetch Cloudflare edge IP via /cdn-cgi/trace
    let edgeIp = 'unknown';
    try {
      const traceResp = await fetch("https://" + request.headers.get("host") + "/cdn-cgi/trace");
      const traceText = await traceResp.text();
      for (const line of traceText.split("\n")) {
        if (line.startsWith("ip=")) {
          edgeIp = line.split("=")[1].trim();
          break;
        }
      }
    } catch (err) {
      edgeIp = 'error fetching edge IP';
    }

    // Full response
    const responseData = {
      clientIP,
      cloudflareEdgeIP: edgeIp,
      cloudflareInfo,
      serverInfo,
      userAgent: request.headers.get('user-agent') || 'unknown',
    };

    return new Response(JSON.stringify(responseData, null, 2), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
