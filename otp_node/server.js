require('dotenv').config();
const express = require('express');
const cors = require('cors');
const nodemailer = require('nodemailer');
const crypto = require('crypto');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// In-memory OTP store: { email: { code, expiresAt, lastSentAt, attempts } }
const OTP_STORE = new Map();

// Gmail transporter (use App Password)
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

// Helpers
function genCode() {
  return crypto.randomInt(0, 1_000_000).toString().padStart(6, '0');
}

function maskEmail(e) {
  if (!e) return '';
  const [u, d = ''] = e.split('@');
  const dom = d.split('.');
  const u2 = u.length > 2 ? (u[0] + '***' + u.slice(-1)) : (u + '***');
  const dom2 = dom[0] ? (dom[0][0] + '***') : '';
  const tld = dom[1] ? dom.slice(1).join('.') : '';
  return `${u2}@${dom2}${tld ? '.' + tld : ''}`;
}

// Request OTP
app.post('/auth/otp/request', async (req, res) => {
  try {
    const email = (req.body.email || '').trim().toLowerCase();
    if (!email || !email.includes('@') || !email.includes('.')) {
      return res.status(400).json({ error: 'Valid email required' });
    }

    const rec = OTP_STORE.get(email);
    const now = Date.now();
    if (rec && rec.lastSentAt && now - rec.lastSentAt < 30_000) {
      const wait = Math.ceil((30_000 - (now - rec.lastSentAt)) / 1000);
      return res.status(429).json({ error: `Please wait ${wait}s before requesting another code` });
    }

    const code = genCode();
    const expiresAt = now + 10 * 60 * 1000; // 10 minutes
    OTP_STORE.set(email, { code, expiresAt, lastSentAt: now, attempts: 0 });

    await transporter.sendMail({
      from: process.env.SMTP_FROM || process.env.SMTP_USER,
      to: email,
      subject: 'Your Login Code',
      text: `Your one-time login code is: ${code}\nIt expires in 10 minutes.`,
    });

    if (process.env.DEBUG_OTP) {
      console.log(`[OTP] sent to ${email}: ${code}`);
    }
    res.json({ ok: true, cooldown: 30, expires_in: 600, masked: maskEmail(email) });
  } catch (err) {
    console.error('OTP send error:', err);
    res.status(500).json({ error: 'Failed to send code. Check SMTP config (Gmail App Password).' });
  }
});

// Verify OTP
app.post('/auth/otp/verify', (req, res) => {
  const email = (req.body.email || '').trim().toLowerCase();
  const code = (req.body.code || '').trim();

  const rec = OTP_STORE.get(email);
  if (!rec) return res.status(400).json({ error: 'No code requested for this email' });
  if (Date.now() > rec.expiresAt) {
    OTP_STORE.delete(email);
    return res.status(400).json({ error: 'Code expired. Request a new one.' });
  }
  if (rec.attempts >= 6) {
    OTP_STORE.delete(email);
    return res.status(429).json({ error: 'Too many attempts. Request a new code.' });
  }
  if (code !== rec.code) {
    rec.attempts += 1;
    OTP_STORE.set(email, rec);
    return res.status(400).json({ error: 'Invalid code' });
  }
  OTP_STORE.delete(email);
  // Demo token (replace with JWT if needed)
  const token = 'demo-' + Buffer.from(email).toString('base64url');
  res.json({ ok: true, token });
});

// Simple health
app.get('/health', (_, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 8787;
app.listen(PORT, () => console.log(`OTP server on http://localhost:${PORT}`));

