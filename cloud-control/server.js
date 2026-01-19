const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3001; // 使用不同端口，避免与用户系统冲突
const CONFIG_FILE = path.join(__dirname, 'configs.json');

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// 初始化配置文件
if (!fs.existsSync(CONFIG_FILE)) {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify({
        "welcome_msg": "欢迎使用云控系统",
        "api_version": "1.0.0"
    }, null, 2));
}

// 读取配置
function getConfigs() {
    return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
}

// 保存配置
function saveConfigs(configs) {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(configs, null, 2));
}

// --- 客户端 API ---

// 通过 key 获取配置值
app.get('/api/config/:key', (req, res) => {
    const configs = getConfigs();
    const key = req.params.key;
    if (key in configs) {
        res.json({ key: key, value: configs[key] });
    } else {
        res.status(404).json({ message: 'Key not found' });
    }
});

// 获取所有配置 (客户端可选)
app.get('/api/configs', (req, res) => {
    res.json(getConfigs());
});

// --- 管理端 API ---

// 获取所有配置列表
app.get('/admin/api/configs', (req, res) => {
    const configs = getConfigs();
    const list = Object.keys(configs).map(key => ({
        key: key,
        value: configs[key]
    }));
    res.json(list);
});

// 新增或修改配置
app.post('/admin/api/configs', (req, res) => {
    const { key, value } = req.body;
    if (!key) return res.status(400).json({ message: 'Key is required' });
    
    const configs = getConfigs();
    configs[key] = value;
    saveConfigs(configs);
    res.json({ message: 'Success', data: { key, value } });
});

// 删除配置
app.delete('/admin/api/configs/:key', (req, res) => {
    const key = req.params.key;
    const configs = getConfigs();
    if (key in configs) {
        delete configs[key];
        saveConfigs(configs);
        res.json({ message: 'Deleted successfully' });
    } else {
        res.status(404).json({ message: 'Key not found' });
    }
});

app.listen(PORT, () => {
    console.log(`Cloud Control System running at http://localhost:${PORT}`);
});
