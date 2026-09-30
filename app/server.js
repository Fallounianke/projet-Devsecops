const express = require('express');
const os = require('os');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.static('public'));

// Endpoint API pour retourner des métriques du Pod
app.get('/api/info', (req, res) => {
  res.json({
    podName: os.hostname(),
    platform: os.platform(),
    uptime: Math.floor(os.uptime()),
    memoryUsage: Math.round(process.memoryUsage().rss / 1024 / 1024) + ' MB',
    timestamp: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`Application démarrée sur le port ${PORT}`);
});