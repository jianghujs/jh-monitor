const assert = require('assert');
const fs = require('fs');
const http = require('http');
const { chromium } = require('playwright-core');

const root = require('path').resolve(__dirname, '..');
const jquery = fs.readFileSync(root + '/route/static/js/jquery-1.10.2.min.js');
const apiKeys = fs.readFileSync(root + '/route/static/app/api-keys.js');
const sharedKey = 'Ui_Shared_Key_' + 'U'.repeat(32);
const maskedPrefix = sharedKey.slice(0, 12) + '…';
let list = [];
let requests = [];

const server = http.createServer((request, response) => {
  if (request.url === '/jquery.js') {
    response.writeHead(200, { 'Content-Type': 'application/javascript' });
    response.end(jquery);
    return;
  }
  if (request.url === '/api-keys.js') {
    response.writeHead(200, { 'Content-Type': 'application/javascript' });
    response.end(apiKeys);
    return;
  }
  if (request.url === '/config/get_api_keys') {
    request.resume();
    request.on('end', () => {
      response.writeHead(200, { 'Content-Type': 'application/json' });
      response.end(JSON.stringify({ status: true, data: {
        csrf_token: 'csrf', panel_api_open: true, scopes: { 'ha:read': '读取云监控主备关系' }, list
      } }));
    });
    return;
  }
  if (request.url === '/config/set_api_key') {
    let body = '';
    request.on('data', chunk => { body += chunk; });
    request.on('end', () => {
      const data = Object.fromEntries(new URLSearchParams(body));
      requests.push(data);
      response.writeHead(data.name === '重复' ? 409 : 200, { 'Content-Type': 'application/json' });
      if (data.name === '重复') {
        response.end(JSON.stringify({ status: false, msg: '该密钥已存在，请使用已有记录或填写其他密钥' }));
        return;
      }
      if (data.action === 'create') {
        list = [{
          key_id: 'created', name: data.name, key_type: data.key_type, key_prefix: maskedPrefix,
          scopes: JSON.parse(data.scopes), is_enabled: true, expires_at: null, remark: '', last_used_at: null
        }];
      }
      response.end(JSON.stringify({ status: true, data: { key_id: 'created', key: sharedKey } }));
    });
    return;
  }
  response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  response.end(`<!doctype html><html><body><div id="root"></div>
    <script src="/jquery.js"></script><script>
    window.messages=[]; window.dialog=null; window.confirmDialog=null;
    window.layer={
      msg:function(message){window.messages.push(message);},
      open:function(options){window.dialog=options; document.body.appendChild(options.content[0]); return 7;},
      close:function(){if(window.dialog&&window.dialog.end){window.dialog.end();} window.dialog=null;},
      confirm:function(message,options,callback){window.confirmDialog={message,callback};}
    };
    </script><script src="/api-keys.js"></script><script>renderPanelApiKeys('#root');</script>
  </body></html>`);
});

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || chromium.executablePath(),
    headless: true, args: ['--no-sandbox']
  });
  const page = await browser.newPage();
  try {
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.locator('.akp-add').click();
    const keyInput = page.locator('[name=key]');
    await keyInput.waitFor();
    assert.equal(await keyInput.getAttribute('type'), 'password');
    assert.equal(await keyInput.inputValue(), '');
    await keyInput.fill(sharedKey);
    await page.locator('.akp-key-toggle').click();
    assert.equal(await keyInput.getAttribute('type'), 'text');
    await page.locator('[name=key_type][value=admin]').check();
    assert.equal(await keyInput.inputValue(), sharedKey);
    await page.locator('[name=key_type][value=normal]').check();
    assert.equal(await keyInput.inputValue(), sharedKey);

    await page.evaluate(() => window.layer.close(7));
    assert.equal(await page.locator('[name=key]').count(), 0);
    await page.locator('.akp-add').click();
    assert.equal(await page.locator('[name=key]').inputValue(), '');
    assert.equal(await page.locator('[name=key]').getAttribute('type'), 'password');

    await page.locator('[name=name]').fill('校验');
    await page.locator('[name=key]').fill('short');
    await page.locator('[name=scope][value="ha:read"]').check();
    await page.evaluate(() => window.dialog.yes(7));
    assert.equal(requests.length, 0);
    assert((await page.evaluate(() => window.messages)).includes('密钥串必须为 32～128 位字母、数字、下划线或短横线'));

    await page.locator('[name=name]').fill('UI 创建');
    await page.locator('[name=key]').fill(sharedKey);
    await page.evaluate(() => window.dialog.yes(7));
    await page.locator('.akp-secret').waitFor();
    assert.equal(requests[0].key, sharedKey);
    assert.equal(await page.locator('.akp-secret').textContent(), maskedPrefix);
    assert(!(await page.content()).includes(sharedKey));
    await page.getByText('编辑', { exact: true }).click();
    assert.equal(await page.locator('[name=key]').count(), 0);
    await page.evaluate(() => window.layer.close(7));

    await page.locator('.akp-add').click();
    await page.locator('[name=name]').fill('重复');
    await page.locator('[name=key]').fill(sharedKey);
    await page.locator('[name=scope][value="ha:read"]').check();
    await page.evaluate(() => window.dialog.yes(7));
    await page.waitForFunction(() => window.messages.includes('该密钥已存在，请使用已有记录或填写其他密钥'));
    assert(!(await page.evaluate(() => window.messages.join('\n'))).includes(sharedKey));
    console.log('API key UI Chromium checks passed');
  } finally {
    await browser.close();
    server.close();
  }
})().catch(error => {
  console.error(error);
  server.close();
  process.exit(1);
});
