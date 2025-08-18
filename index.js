export default {
  async fetch(request) {

    // Fetch Cloudflare trace info to get edge IP
    const traceResp = await fetch("https://" + request.headers.get("host") + "/cdn-cgi/trace");
    const traceText = await traceResp.text();

    let edgeIp = "unknown";
    for (const line of traceText.split("\n")) {
      if (line.startsWith("ip=")) {
        edgeIp = line.split("=")[1].trim();
        break;
      }
    }

    // Custom message with edge IP
    const output = `Hello Bro 👋 — Current Cloudflare IP: ${edgeIp}`;

    return new Response(output, {
      headers: { "content-type": "text/plain" }
    });
  }
}
