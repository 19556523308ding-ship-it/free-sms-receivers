/**
 * extractOtp 离线回归测试（不联网，直接喂真实抓到的短信样本）
 * 用途：验证码提取一旦出错会直接误导用户，必须每次改动后跑一遍。
 * 运行：node tools/test-otp.js
 */
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, '..', 'api', 'reader.js'), 'utf8');
const fn = src.match(/function extractOtp[\s\S]*?\n}\n/);
if (!fn) { console.error('未能从 reader.js 中提取 extractOtp'); process.exit(1); }
// eslint-disable-next-line no-eval
const extractOtp = eval('(' + fn[0].replace('function extractOtp', 'function') + ')');

// 样本全部来自receiveasmsonline 实测抓取的真实短信（含干扰号码）
const CASES = [
  // —— 强特征：Google 风格 G-132619，正文尾部带 10 位干扰号
  ['G-132619 is your Google verification code. 1897373737', '132619'],
  ['G-350333 is your Google verification code.', '350333'],
  // —— 关键字 + 尾部干扰号
  ['986728 is your Amazon OTP. Do not share it with anyone. 011262966', '986728'],
  ['Your verification code is 37583, enjoy! 447872995353', '37583'],
  ['DENT your code is 1231234 valid 5 min', '1231234'],
  ['SmallWorld code: 034635 18337430732', '034635'],
  ['Open www.ncccprime.com/f3, code: 33333-65001897373737', '33333'],
  ['Your one-time passcode is 551204. Do not share.', '551204'],
  // —— 中文短信
  ['【优衣库】您的验证码是 843920，请勿泄露给他人。', '843920'],
  // —— 无「code/otp/验证码」语义、只有裸长号：不应该硬凑出一个码
  ['Call +1 2025550143 for support', null],
  ['Your order 447872995353 has shipped', null],
  // —— 号码被打散成 3 位 + 2 位，不构成4-8 位独立码
  ['285 33 is your Instagram code. Don\'t share it.', null],
  // —— 正常的安全码短信仍要能提出来
  ['Your PayPal security code is 214053', '214053'],
];

let pass = 0;
for (const [text, expected] of CASES) {
  const got = extractOtp(text);
  const ok = got === expected;
  if (ok) pass++;
  const mark = ok ? '  OK  ' : '  FAIL';
  console.log(
    mark +
    ' exp=' + String(expected).padEnd(8) +
    ' got=' + String(got).padEnd(9) +
    ' | ' + text.slice(0, 60)
  );
}
console.log('\n通过 ' + pass + '/' + CASES.length);
process.exit(pass === CASES.length ? 0 : 1);