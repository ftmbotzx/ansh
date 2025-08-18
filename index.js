addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url);

  if (url.pathname === '/ip') {
    // Client IP
    const clientIP = request.headers.get('cf-connecting-ip') || 'Unknown';

    // Server (website) details
    const serverInfo = {
      protocol: url.protocol,
      hostname: url.hostname,
      pathname: url.pathname,
      fullURL: url.href,
      origin: url.origin,
      port: url.port || 'default',
    };

    // Cloudflare info if available
    const cfInfo = request.cf || {};
    const cloudflareInfo = {
      region: cfInfo.region || 'Unknown',
      city: cfInfo.city || 'Unknown',
      asn: cfInfo.asn || 'Unknown',
      country: cfInfo.country || 'Unknown',
      colo: cfInfo.colo || 'Unknown',
    };

    const info = {
      clientIP,
      serverInfo,
      cloudflareInfo,
      userAgent: request.headers.get('user-agent') || 'Unknown',
    };

    return new Response(JSON.stringify(info, null, 2), {
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // Default: countdown + calculator page
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Countdown Calculator</title>
      <script>
        let countdown = 10;

        function startCountdown() {
          const countdownEl = document.getElementById('countdown');
          const interval = setInterval(() => {
            countdownEl.textContent = countdown;
            countdown--;
            if (countdown < 0) {
              clearInterval(interval);
              document.getElementById('calculator').style.display = 'block';
              countdownEl.style.display = 'none';
            }
          }, 1000);
        }

        function calculate() {
          const a = parseFloat(document.getElementById('num1').value);
          const b = parseFloat(document.getElementById('num2').value);
          const op = document.getElementById('operator').value;
          let result = 0;
          if(op === '+') result = a + b;
          if(op === '-') result = a - b;
          if(op === '*') result = a * b;
          if(op === '/') result = a / b;
          document.getElementById('result').textContent = 'Result: ' + result;
        }

        window.onload = startCountdown;
      </script>
    </head>
    <body>
      <h1>Countdown: <span id="countdown">10</span> seconds</h1>

      <div id="calculator" style="display:none;">
        <h2>Simple Calculator</h2>
        <input type="number" id="num1" placeholder="Number 1">
        <select id="operator">
          <option value="+">+</option>
          <option value="-">-</option>
          <option value="*">*</option>
          <option value="/">/</option>
        </select>
        <input type="number" id="num2" placeholder="Number 2">
        <button onclick="calculate()">Calculate</button>
        <p id="result"></p>
      </div>
    </body>
    </html>
  `;
  return new Response(html, { headers: { 'Content-Type': 'text/html' } });
}
