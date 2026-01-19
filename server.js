const express = require('express');
const fs = require('fs');
const path = require('path');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();
const PORT = 3000;
const DATA_FILE = path.join(__dirname, 'users.json');

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// 初始化数据文件
if (!fs.existsSync(DATA_FILE)) {
    fs.writeFileSync(DATA_FILE, JSON.stringify({ users: [] }));
}

// 获取所有用户数据
const getUsers = () => {
    const data = fs.readFileSync(DATA_FILE);
    return JSON.parse(data).users;
};

// 保存用户数据
const saveUsers = (users) => {
    fs.writeFileSync(DATA_FILE, JSON.stringify({ users }, null, 2));
};

// 注册
app.post('/api/register', (req, res) => {
    const { username, password, email } = req.body;
    const users = getUsers();

    if (users.find(u => u.username === username)) {
        return res.status(400).json({ message: '用户名已存在' });
    }

    const newUser = {
        username,
        password, // 实际生产环境应使用 hash
        email,
        favorites: [],
        createdAt: new Date()
    };

    users.push(newUser);
    saveUsers(users);

    res.json({ message: '注册成功', user: { username } });
});

// 登录
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    const users = getUsers();

    const user = users.find(u => u.username === username && u.password === password);
    if (!user) {
        return res.status(401).json({ message: '用户名或密码错误' });
    }

    res.json({
        message: '登录成功',
        user: { username, favorites: user.favorites }
    });
});

// 同步收藏
app.post('/api/sync', (req, res) => {
    const { username, favorites } = req.body;
    const users = getUsers();

    const userIndex = users.findIndex(u => u.username === username);
    if (userIndex === -1) {
        return res.status(404).json({ message: '用户不存在' });
    }

    users[userIndex].favorites = favorites;
    users[userIndex].updatedAt = new Date();
    saveUsers(users);

    res.json({ message: '同步成功' });
});

// 获取收藏
app.get('/api/favorites/:username', (req, res) => {
    const { username } = req.params;
    const users = getUsers();

    const user = users.find(u => u.username === username);
    if (!user) {
        return res.status(404).json({ message: '用户不存在' });
    }

    res.json({ favorites: user.favorites });
});

app.listen(PORT, () => {
    console.log(`User system backend running at http://localhost:${PORT}`);
});
