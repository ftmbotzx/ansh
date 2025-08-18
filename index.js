export default {
  async fetch(request) {

    // /cdn-cgi/trace se Cloudflare edge IP nikalte hain
    const traceResp = await fetch("https://" + request.headers.get("host") + "/cdn-cgi/trace");
    const traceText = await traceResp.text();

    let edgeIp = "unknown";
    for (const line of traceText.split("\n")) {
      if (line.startsWith("ip=")) {
        edgeIp = line.split("=")[1].trim();
        break;
      }
    }

    // 👇 yaha apna custom text likho, jaise "Hello from Cloudflare IP: <ip>"
    const output = Hello Bro 👋 — Current Cloudflare IP: ${edgeIp}

    return new Response(output, {
      headers: { "content-type": "text/plain" }
    })
  }
}
