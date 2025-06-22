// server.js
const express = require('express');
const readline = require('readline');
const app = express();
const PORT = process.env.PORT || 3000;

let messages = [];
let results = [];

app.use(express.json());

// Gửi lệnh từ server tới client
app.get('/receive', (req, res) => {
  res.send(messages);
  messages = []; // Xoá sau khi gửi
});

// Client gửi kết quả về đây
app.post('/send', (req, res) => {
  if (req.body.result) {
    results.push(req.body.result);
    console.log(`[CLIENT] ${req.body.result}`);
  }
  res.send({ status: 'OK' });
});

// Kết quả tổng hợp nếu cần xem lại
app.get('/results', (req, res) => {
  res.send(results);
});

app.listen(PORT, () => {
  console.log(`Relay server HTTP đang chạy tại cổng ${PORT}`);
  askInput();
});

function askInput() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  rl.setPrompt('>>> ');
  rl.prompt();

  rl.on('line', (line) => {
    const cmd = line.trim();
    if (cmd) {
      messages.push({ cmd });
    }
    rl.prompt();
  });
}
