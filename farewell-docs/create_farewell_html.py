# -*- coding: utf-8 -*-
html = '''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>送別会 会費収支</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"游ゴシック",YuGothic,"Helvetica Neue",sans-serif;
  background:#f0f2f5;color:#1a1a1a;font-size:15px;
}
.wrap{max-width:480px;margin:0 auto;padding:12px}

/* ヘッダー */
.header{
  background:linear-gradient(135deg,#1F3864,#2e5fa3);
  color:#fff;border-radius:16px;padding:20px 16px 16px;margin-bottom:12px;
  text-align:center;
}
.header h1{font-size:20px;font-weight:700;letter-spacing:.5px}
.header .sub{font-size:13px;opacity:.85;margin-top:6px}
.header .meta{
  display:flex;gap:12px;justify-content:center;margin-top:12px;
}
.header .meta span{
  background:rgba(255,255,255,.18);border-radius:8px;
  padding:4px 12px;font-size:12px;
}

/* カード */
.card{background:#fff;border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card-title{
  font-size:13px;font-weight:700;color:#1F3864;
  border-left:4px solid #1F3864;padding-left:8px;margin-bottom:12px;letter-spacing:.3px;
}

/* 収支サマリーの大きな数値 */
.summary-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.summary-box{
  background:#f7f9fc;border-radius:10px;padding:10px 12px;text-align:center;
}
.summary-box.full{grid-column:1/-1}
.summary-box .label{font-size:11px;color:#666;margin-bottom:4px}
.summary-box .value{font-size:20px;font-weight:700;color:#1F3864}
.summary-box .value.red{color:#c00}
.summary-box .value.green{color:#0a7a0a}
.summary-box .value.gold{color:#8a6000}
.summary-box.highlight{background:#e8f0fe}

/* 残額ビッグ表示 */
.big-alert{
  border-radius:14px;padding:18px 16px;text-align:center;
  margin-bottom:12px;transition:background .3s;
}
.big-alert .label{font-size:13px;font-weight:600;margin-bottom:6px;opacity:.9}
.big-alert .amount{font-size:32px;font-weight:800;letter-spacing:-1px}
.big-alert .msg{font-size:13px;margin-top:8px;font-weight:600}
.big-alert.ok{background:#e6f4ea;color:#0a7a0a}
.big-alert.warn{background:#fce8e6;color:#c00;animation:pulse .8s ease-in-out infinite alternate}
@keyframes pulse{from{opacity:1}to{opacity:.75}}

/* 入力テーブル */
.input-table{width:100%;border-collapse:collapse}
.input-table th{
  background:#1F3864;color:#fff;font-size:12px;font-weight:600;
  padding:8px 6px;text-align:center;
}
.input-table td{
  border-bottom:1px solid #eee;padding:8px 6px;font-size:14px;
  vertical-align:middle;
}
.input-table td.name{font-weight:600;color:#333}
.input-table td.num{text-align:right;font-variant-numeric:tabular-nums}
.input-table tr:nth-child(even) td{background:#fafafa}
.input-table tr.total td{background:#D6E4F0;font-weight:700}

/* 数値入力欄 */
.num-input{
  width:100%;border:2px solid #f0c040;border-radius:8px;
  padding:8px 10px;font-size:15px;text-align:right;
  background:#FFFDE7;outline:none;
  font-family:inherit;
}
.num-input:focus{border-color:#e6a800;background:#fff8dc}

/* 参加者リスト（折りたたみ） */
details summary{
  font-size:13px;font-weight:700;color:#1F3864;
  border-left:4px solid #1F3864;padding-left:8px;
  cursor:pointer;user-select:none;list-style:none;
  display:flex;justify-content:space-between;align-items:center;
}
details summary::after{content:"▼";font-size:10px;color:#888}
details[open] summary::after{content:"▲"}
details summary::-webkit-details-marker{display:none}

.member-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:13px}
.member-table th{background:#1F3864;color:#fff;padding:6px 4px;text-align:center;font-size:11px}
.member-table td{border-bottom:1px solid #eee;padding:6px 4px;text-align:center}
.member-table tr:nth-child(even) td{background:#fafafa}
.badge{display:inline-block;border-radius:4px;padding:1px 6px;font-size:10px;font-weight:700}
.badge.boss{background:#dce8ff;color:#1F3864}
.badge.general{background:#f0f0f0;color:#444}
.badge.invite{background:#ffe0e0;color:#c00}

/* 返金カード */
.refund-card{
  background:linear-gradient(135deg,#fff8dc,#ffe082);
  border-radius:14px;padding:16px;margin-bottom:12px;text-align:center;
  display:none;
}
.refund-card.show{display:block}
.refund-card .label{font-size:12px;color:#6b4f00;margin-bottom:6px}
.refund-card .amount{font-size:28px;font-weight:800;color:#7b4900}
.refund-card .note{font-size:11px;color:#8a6000;margin-top:4px}

.footer{text-align:center;font-size:11px;color:#aaa;padding:8px 0 20px}
</style>
</head>
<body>
<div class="wrap">

<!-- ヘッダー -->
<div class="header">
  <h1>送別会 会費収支報告</h1>
  <div class="sub">2026年4月17日</div>
  <div class="meta">
    <span>参加 16名</span>
    <span>招待 3名</span>
    <span>負担 13名</span>
  </div>
</div>

<!-- 収支サマリー -->
<div class="card">
  <div class="card-title">収支サマリー</div>
  <div class="summary-grid">
    <div class="summary-box">
      <div class="label">収入合計</div>
      <div class="value">152,000円</div>
    </div>
    <div class="summary-box">
      <div class="label">固定支出</div>
      <div class="value">19,386円</div>
    </div>
    <div class="summary-box highlight full">
      <div class="label">飲食に使える予算（自動計算）</div>
      <div class="value" style="font-size:24px">132,614円</div>
    </div>
  </div>
</div>

<!-- 食事・お酒入力エリア -->
<div class="card">
  <div class="card-title">食事・お酒 予算管理　<span style="font-size:11px;color:#888;font-weight:400">← 黄色欄に入力</span></div>
  <table class="input-table">
    <thead>
      <tr>
        <th style="width:28%">項目</th>
        <th style="width:24%">予算</th>
        <th style="width:24%">実績</th>
        <th style="width:24%">残額</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="name">食事代</td>
        <td><input class="num-input" id="food_budget" type="number" inputmode="numeric" placeholder="0" oninput="calc()"></td>
        <td><input class="num-input" id="food_actual" type="number" inputmode="numeric" placeholder="0" oninput="calc()"></td>
        <td class="num" id="food_remain">—</td>
      </tr>
      <tr>
        <td class="name">お酒代</td>
        <td><input class="num-input" id="drink_budget" type="number" inputmode="numeric" placeholder="0" oninput="calc()"></td>
        <td><input class="num-input" id="drink_actual" type="number" inputmode="numeric" placeholder="0" oninput="calc()"></td>
        <td class="num" id="drink_remain">—</td>
      </tr>
      <tr class="total">
        <td class="name">合計</td>
        <td class="num" id="total_budget">—</td>
        <td class="num" id="total_actual">—</td>
        <td class="num" id="total_remain">—</td>
      </tr>
    </tbody>
  </table>
</div>

<!-- あと注文できる金額 -->
<div class="big-alert ok" id="alert_box">
  <div class="label">あと注文できる金額</div>
  <div class="amount" id="alert_amount">132,614円</div>
  <div class="msg" id="alert_msg">✓ まだ余裕あり</div>
</div>

<!-- 差引残高 -->
<div class="card">
  <div class="card-title">差引残高</div>
  <div class="summary-grid">
    <div class="summary-box">
      <div class="label">飲食費実績</div>
      <div class="value" id="food_total_val">—</div>
    </div>
    <div class="summary-box">
      <div class="label">差引残高</div>
      <div class="value" id="balance_val">4,614円</div>
    </div>
    <div class="summary-box full">
      <div class="label">一般参加者の実質負担額（8,000円 − 返金額）</div>
      <div class="value" id="per_person_val">—</div>
    </div>
  </div>
</div>

<!-- 返金カード -->
<div class="refund-card" id="refund_card">
  <div class="label">💰 余剰金が発生！ 1人あたり返金額（上司除く一般9名）</div>
  <div class="amount" id="refund_amount">—</div>
  <div class="note">対象：幸田・宮元・武田・北野・ソラウィット・スメート・エドセル・マール・ジャッカパン</div>
</div>

<!-- 固定支出内訳 -->
<div class="card">
  <div class="card-title">固定支出内訳</div>
  <table class="input-table">
    <thead><tr><th>項目</th><th>金額</th></tr></thead>
    <tbody>
      <tr><td>記念品</td><td class="num">15,806円</td></tr>
      <tr><td>高速代</td><td class="num">580円</td></tr>
      <tr><td>交通費</td><td class="num">3,000円</td></tr>
      <tr class="total"><td>合計</td><td class="num">19,386円</td></tr>
    </tbody>
  </table>
</div>

<!-- 参加者一覧（折りたたみ） -->
<div class="card">
  <details>
    <summary>参加者一覧（タップで展開）</summary>
    <table class="member-table">
      <thead>
        <tr><th>氏名</th><th>区分</th><th>会費</th><th>支援金</th><th>負担額</th></tr>
      </thead>
      <tbody>
        <tr><td>渡辺</td><td><span class="badge boss">上司</span></td><td>8,000</td><td>12,000</td><td>20,000</td></tr>
        <tr><td>中村</td><td><span class="badge boss">上司</span></td><td>8,000</td><td>12,000</td><td>20,000</td></tr>
        <tr><td>福岡</td><td><span class="badge boss">上司</span></td><td>8,000</td><td>12,000</td><td>20,000</td></tr>
        <tr><td>板倉</td><td><span class="badge boss">上司</span></td><td>8,000</td><td>12,000</td><td>20,000</td></tr>
        <tr><td>幸田</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>宮元</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>武田</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>北野</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>ソラウィット</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>スメート</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>エドセル</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>マール</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>ジャッカパン</td><td><span class="badge general">一般</span></td><td>8,000</td><td>—</td><td>8,000</td></tr>
        <tr><td>史</td><td><span class="badge invite">招待</span></td><td>—</td><td>—</td><td>0</td></tr>
        <tr><td>大川</td><td><span class="badge invite">招待</span></td><td>—</td><td>—</td><td>0</td></tr>
        <tr><td>パユット</td><td><span class="badge invite">招待</span></td><td>—</td><td>—</td><td>0</td></tr>
        <tr class="total"><td colspan="4">合計</td><td>152,000</td></tr>
      </tbody>
    </table>
  </details>
</div>

<div class="footer">※ 入力値はこのページ内のみで保持されます（保存されません）</div>

</div><!-- /wrap -->

<script>
const INCOME   = 152000;
const FIXED    = 19386;
const FOOD_BUDGET = INCOME - FIXED; // 132614

function v(id){ return parseFloat(document.getElementById(id).value)||0; }
function fmt(n){ return n.toLocaleString('ja-JP')+'円'; }

function calc(){
  const fb = v('food_budget'),  fa = v('food_actual');
  const db = v('drink_budget'), da = v('drink_actual');

  const fb_entered = fb>0, fa_entered = fa>0;
  const db_entered = db>0, da_entered = da>0;

  // 食事残額
  const f_rem = (fb_entered||fa_entered) ? fb-fa : null;
  const d_rem = (db_entered||da_entered) ? db-da : null;

  setRemain('food_remain',  f_rem);
  setRemain('drink_remain', d_rem);

  // 合計
  const bud_any = fb_entered||db_entered;
  const act_any = fa_entered||da_entered;
  document.getElementById('total_budget').textContent = bud_any ? fmt(fb+db) : '—';
  document.getElementById('total_actual').textContent = act_any ? fmt(fa+da) : '—';

  const t_rem = (bud_any||act_any) ? (fb+db)-(fa+da) : null;
  setRemain('total_remain', t_rem);

  // あと注文できる金額: 実績があれば実績ベース、なければ予算ベース
  const actual_total = fa+da;
  const budget_total = fb+db;
  let orderLeft;
  if(act_any){
    orderLeft = FOOD_BUDGET - actual_total;
  } else if(bud_any){
    orderLeft = FOOD_BUDGET - budget_total;
  } else {
    orderLeft = FOOD_BUDGET;
  }

  const alertBox    = document.getElementById('alert_box');
  const alertAmount = document.getElementById('alert_amount');
  const alertMsg    = document.getElementById('alert_msg');
  alertAmount.textContent = fmt(Math.abs(orderLeft));
  if(orderLeft < 0){
    alertBox.className = 'big-alert warn';
    alertAmount.textContent = '▲'+fmt(Math.abs(orderLeft));
    alertMsg.textContent = '⚠ これ以上注文すると赤字！';
  } else {
    alertBox.className = 'big-alert ok';
    alertMsg.textContent = '✓ まだ余裕あり';
  }

  // 差引残高: 実績があれば実績ベース、なければ計画値(128000)
  const foodCost = act_any ? actual_total : 128000;
  const balance  = INCOME - FIXED - foodCost;

  document.getElementById('food_total_val').textContent = act_any ? fmt(actual_total) : '未入力';
  const balEl = document.getElementById('balance_val');
  balEl.textContent = fmt(Math.abs(balance));
  balEl.className   = 'value '+(balance<0?'red':'green');

  // 一般参加者の実質負担額 = 8,000円 - 返金額
  const refundPer = balance > 0 ? Math.round(balance / 9) : 0;
  document.getElementById('per_person_val').textContent = fmt(8000 - refundPer);

  // 返金額（上司除く一般9名）
  const refundCard = document.getElementById('refund_card');
  const refundAmt  = document.getElementById('refund_amount');
  if(balance > 0 && act_any){
    refundCard.className = 'refund-card show';
    refundAmt.textContent = fmt(Math.round(balance/9))+'／人';
  } else {
    refundCard.className = 'refund-card';
  }
}

function setRemain(id, val){
  const el = document.getElementById(id);
  if(val===null){ el.textContent='—'; el.style.color=''; return; }
  el.textContent = val<0 ? '▲'+Math.abs(val).toLocaleString('ja-JP')+'円' : fmt(val);
  el.style.color = val<0 ? '#c00' : '#0a7a0a';
  el.style.fontWeight = val<0 ? '700' : '600';
}
</script>
</body>
</html>'''

with open('C:/Users/SEIGI-N13/Desktop/260417送別会 会費.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('完了')
