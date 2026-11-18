// ==UserScript==
// @name         FCFL: send this player page to the Stats Converter
// @namespace    https://github.com/FabianZettl/fcfl-stats-converter
// @version      1.0
// @description  Button on SoFIFA and FMInside player pages: sends the page to the running FCFL Stats Converter, which opens the player there with the conversion ready (instead of Ctrl+A, Ctrl+C, paste).
// @match        https://sofifa.com/player/*
// @match        https://*.sofifa.com/player/*
// @match        https://fminside.net/players/*
// @match        https://*.fminside.net/players/*
// @grant        GM_xmlhttpRequest
// @grant        GM_openInTab
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==
(function () {
  'use strict';
  const FCFL = 'http://127.0.0.1:8790';   // port of the converter (start.sh --port to change it)
  const b = document.createElement('button');
  b.textContent = '→ FCFL';
  b.title = 'Send this player to the FCFL Stats Converter';
  b.style.cssText = 'position:fixed;right:16px;bottom:16px;z-index:99999;padding:10px 16px;border:0;border-radius:8px;background:#e0393f;color:#fff;font:600 14px sans-serif;cursor:pointer;box-shadow:0 2px 8px #0006';
  const say = t => { b.textContent = t; setTimeout(() => (b.textContent = '→ FCFL'), 3500); };
  b.onclick = () => {
    const h1 = (document.querySelector('h1') || {}).textContent || '';
    const title = (document.title || '').split(/\s[-|(]\s?|\s\(/)[0];
    const og = (document.querySelector('meta[property="og:title"]') || {}).content || '';
    GM_xmlhttpRequest({
      method: 'POST', url: FCFL + '/api/paste', headers: { 'Content-Type': 'application/json' },
      data: JSON.stringify({ names: [h1, title, og.split(/\s[-|(]\s?|\s\(/)[0]].map(s => s.trim()).filter(Boolean), url: location.href, text: document.body.innerText }),
      onload: r => {
        let j = {};
        try { j = JSON.parse(r.responseText); } catch (e) {}
        if (j.ok) { say('sent'); GM_openInTab(FCFL + '/', { active: true }); }
        else say(j.msg || 'FCFL said no');
      },
      onerror: () => say('FCFL is not running?'),
    });
  };
  document.body.appendChild(b);
})();
