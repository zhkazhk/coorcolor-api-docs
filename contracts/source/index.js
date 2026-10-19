const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const { usersDB, addressesDB, engineersDB, ordersDB, ratingsDB, adminsDB, couponsDB, referralsDB, rebatesDB, productsDB, reviewsDB, initDatabase } = require('./database');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const app = express();
const PORT = process.env.PORT || 3000;
const JWT_SECRET = '<REDACTED:jwt-secret>';

app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../admin')));

app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, '../admin/index.html'));
});

app.get('/', (req, res) => {
  res.json({ message: 'CoorColor打印机维修服务后端API', version: '1.0.0' });
});

const generateOrderNo = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const random = String(Math.floor(Math.random() * 10000)).padStart(4, '0');
  return `CK${year}${month}${day}${random}`;
};

const validatePhone = (phone) => {
  return /^1[3-9]\d{9}$/.test(phone);
};

const validateOrderData = (req, res, next) => {
  const { serviceType, brand, problemDesc, appointmentDate, appointmentTime, contactName, contactPhone, serviceAddress } = req.body;
  
  const errors = [];
  
  if (!serviceType) errors.push('服务类型不能为空');
  if (!brand) errors.push('品牌不能为空');
  if (!problemDesc) errors.push('问题描述不能为空');
  if (!appointmentDate) errors.push('预约日期不能为空');
  if (!appointmentTime) errors.push('预约时间不能为空');
  if (!contactName || contactName.trim().length < 2) errors.push('请输入正确的联系人姓名');
  if (!contactPhone || !validatePhone(contactPhone)) errors.push('请输入正确的手机号');
  if (!serviceAddress || serviceAddress.trim().length < 5) errors.push('请输入详细的服务地址');
  
  if (errors.length > 0) {
    return res.status(400).json({ code: -1, message: errors.join('；') });
  }
  
  next();
};

app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  await adminsDB.read();
  const admin = adminsDB.data.admins.find(a => a.username === username);
  if (!admin) return res.status(401).json({ code: -1, message: '用户不存在' });
  if (bcrypt.compareSync(password, admin.password)) {
    const token = jwt.sign({ id: admin.id, username: admin.username }, JWT_SECRET, { expiresIn: '24h' });
    res.json({ code: 0, data: { token, username: admin.username } });
  } else {
    res.status(401).json({ code: -1, message: '密码错误' });
  }
});

app.get('/api/orders', async (req, res) => {
  const { status } = req.query;
  await ordersDB.read();
  let ordersList = ordersDB.data.orders;
  if (status && status !== 'all') {
    ordersList = ordersList.filter(o => o.status === status);
  }
  ordersList.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  res.json({ code: 0, data: ordersList });
});

app.post('/api/orders', validateOrderData, async (req, res) => {
  const orderData = req.body;
  const orderNo = generateOrderNo();
  const order = {
    id: Date.now().toString(),
    order_no: orderNo,
    service_type: orderData.serviceType || orderData.service_type,
    brand: orderData.brand,
    model: orderData.model || '',
    problem_desc: orderData.problemDesc || orderData.problem_desc,
    urgency: orderData.urgency || 'normal',
    photos: orderData.photos || [],
    position: orderData.position || null,
    appointment_date: orderData.appointmentDate || orderData.appointment_date,
    appointment_time: orderData.appointmentTime || orderData.appointment_time,
    contact_name: orderData.contactName || orderData.contact_name,
    contact_phone: orderData.contactPhone || orderData.contact_phone,
    service_address: orderData.serviceAddress || orderData.service_address,
    remark: orderData.remark || '',
    status: 'pending',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  await ordersDB.read();
  ordersDB.data.orders.push(order);
  await ordersDB.write();
  res.json({ code: 0, data: { id: order.id, order_no: order.order_no } });
});

app.put('/api/orders/:id/cancel', async (req, res) => {
  await ordersDB.read();
  const order = ordersDB.data.orders.find(o => o.id === req.params.id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  order.status = 'canceled';
  order.updated_at = new Date().toISOString();
  await ordersDB.write();
  res.json({ code: 0, data: null });
});

app.put('/api/admin/orders/:id/status', async (req, res) => {
  const { status, engineer_id } = req.body;
  await ordersDB.read();
  const order = ordersDB.data.orders.find(o => o.id === req.params.id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  order.status = status;
  if (engineer_id) order.engineer_id = engineer_id;
  order.updated_at = new Date().toISOString();
  await ordersDB.write();
  res.json({ code: 0, data: null });
});

app.post('/api/orders/:id/rate', async (req, res) => {
  const { rating, comment } = req.body;
  await ratingsDB.read();
  ratingsDB.data.ratings.push({
    id: Date.now().toString(),
    order_id: req.params.id,
    rating,
    comment: comment || '',
    created_at: new Date().toISOString()
  });
  await ratingsDB.write();
  
  await ordersDB.read();
  const order = ordersDB.data.orders.find(o => o.id === req.params.id);
  if (order) {
    order.status = 'completed';
    order.updated_at = new Date().toISOString();
    await ordersDB.write();
  }
  res.json({ code: 0, data: null });
});

app.get('/api/engineers', async (req, res) => {
  await engineersDB.read();
  const engineersList = engineersDB.data.engineers.sort((a, b) => a.id.localeCompare(b.id));
  res.json({ code: 0, data: engineersList });
});

// 工程师上报位置
app.post('/api/engineers/:id/position', async (req, res) => {
  const { latitude, longitude } = req.body;
  if (!latitude || !longitude) {
    return res.status(400).json({ code: -1, message: '位置参数不完整' });
  }

  await engineersDB.read();
  const engineer = engineersDB.data.engineers.find(e => e.id === req.params.id);
  if (!engineer) {
    return res.status(404).json({ code: -1, message: '工程师不存在' });
  }

  engineer.position = {
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    updated_at: new Date().toISOString()
  };
  engineer.updated_at = new Date().toISOString();
  await engineersDB.write();

  res.json({ code: 0, data: engineer.position });
});

// 获取订单详情（带工程师位置）
app.get('/api/orders/:id', async (req, res) => {
  await ordersDB.read();
  const order = ordersDB.data.orders.find(o => o.id === req.params.id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  
  if (order.engineer_id) {
    await engineersDB.read();
    const engineer = engineersDB.data.engineers.find(e => e.id === order.engineer_id);
    order.engineer_name = engineer ? engineer.name : '';
    order.engineer_phone = engineer ? engineer.phone : '';
    order.engineer_position = engineer ? engineer.position : null;
  }
  res.json({ code: 0, data: order });
});

const verificationCodes = {};

app.get('/api/user/info', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.json({ code: 0, data: { nickname: '用户', phone: '' } });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    await usersDB.read();
    const user = usersDB.data.users.find(u => u.phone === decoded.phone);
    if (user) {
      res.json({ code: 0, data: { nickname: user.nickname || '用户', phone: user.phone } });
    } else {
      res.json({ code: 0, data: { nickname: '用户', phone: decoded.phone || '' } });
    }
  } catch (err) {
    res.json({ code: 0, data: { nickname: '用户', phone: '' } });
  }
});

app.put('/api/user/info', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ code: -1, message: '请先登录' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const { nickname, phone } = req.body;
    
    await usersDB.read();
    let user = usersDB.data.users.find(u => u.phone === decoded.phone);
    
    if (user) {
      if (nickname) user.nickname = nickname;
      if (phone) user.phone = phone;
      user.updated_at = new Date().toISOString();
    } else {
      user = {
        id: Date.now().toString(),
        phone: decoded.phone,
        nickname: nickname || '用户',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      usersDB.data.users.push(user);
    }
    
    await usersDB.write();
    res.json({ code: 0, data: { nickname: user.nickname, phone: user.phone } });
  } catch (err) {
    res.status(401).json({ code: -1, message: '登录已过期' });
  }
});

app.post('/api/user/send-code', (req, res) => {
  const { phone } = req.body;
  
  if (!phone || phone.length !== 11) {
    return res.status(400).json({ code: -1, message: '请输入正确的手机号' });
  }
  
  const code = String(Math.floor(100000 + Math.random() * 900000));
  verificationCodes[phone] = {
    code,
    expiresAt: Date.now() + 5 * 60 * 1000
  };
  
  console.log(`发送验证码 ${code} 到 ${phone}`);
  
  res.json({ code: 0, data: { message: '验证码已发送' } });
});

app.post('/api/user/bind-phone', (req, res) => {
  const { phone, code } = req.body;
  
  if (!phone || phone.length !== 11) {
    return res.status(400).json({ code: -1, message: '请输入正确的手机号' });
  }
  
  if (!code || code.length !== 6) {
    return res.status(400).json({ code: -1, message: '请输入6位验证码' });
  }
  
  const stored = verificationCodes[phone];
  
  if (!stored) {
    return res.status(400).json({ code: -1, message: '请先获取验证码' });
  }
  
  if (Date.now() > stored.expiresAt) {
    delete verificationCodes[phone];
    return res.status(400).json({ code: -1, message: '验证码已过期' });
  }
  
  if (stored.code !== code) {
    return res.status(400).json({ code: -1, message: '验证码错误' });
  }
  
  delete verificationCodes[phone];
  
  res.json({ code: 0, data: { phone } });
});

app.get('/api/user/addresses', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ code: -1, message: '请先登录' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    await addressesDB.read();
    const addresses = addressesDB.data.addresses
      .filter(a => a.phone === decoded.phone)
      .sort((a, b) => (b.is_default ? 1 : 0) - (a.is_default ? 1 : 0));
    res.json({ code: 0, data: addresses });
  } catch (err) {
    res.status(401).json({ code: -1, message: '登录已过期' });
  }
});

app.post('/api/user/addresses', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ code: -1, message: '请先登录' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const { contact_name, contact_phone, province, city, district, address, is_default } = req.body;
    
    if (!contact_name || !contact_phone || !address) {
      return res.status(400).json({ code: -1, message: '请填写完整的地址信息' });
    }
    
    await addressesDB.read();
    
    if (is_default) {
      addressesDB.data.addresses.forEach(a => a.is_default = false);
    }
    
    const addressData = {
      id: Date.now().toString(),
      phone: decoded.phone,
      contact_name,
      contact_phone,
      province: province || '',
      city: city || '',
      district: district || '',
      address,
      is_default: is_default || false,
      created_at: new Date().toISOString()
    };
    
    addressesDB.data.addresses.push(addressData);
    await addressesDB.write();
    
    res.json({ code: 0, data: addressData });
  } catch (err) {
    res.status(401).json({ code: -1, message: '登录已过期' });
  }
});

app.put('/api/user/addresses/:id', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ code: -1, message: '请先登录' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    const { contact_name, contact_phone, province, city, district, address, is_default } = req.body;
    
    await addressesDB.read();
    const addr = addressesDB.data.addresses.find(a => a.id === req.params.id && a.phone === decoded.phone);
    
    if (!addr) {
      return res.status(404).json({ code: -1, message: '地址不存在' });
    }
    
    if (is_default) {
      addressesDB.data.addresses.forEach(a => a.is_default = false);
    }
    
    if (contact_name) addr.contact_name = contact_name;
    if (contact_phone) addr.contact_phone = contact_phone;
    if (province !== undefined) addr.province = province;
    if (city !== undefined) addr.city = city;
    if (district !== undefined) addr.district = district;
    if (address) addr.address = address;
    if (is_default !== undefined) addr.is_default = is_default;
    addr.updated_at = new Date().toISOString();
    
    await addressesDB.write();
    res.json({ code: 0, data: addr });
  } catch (err) {
    res.status(401).json({ code: -1, message: '登录已过期' });
  }
});

app.delete('/api/user/addresses/:id', async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ code: -1, message: '请先登录' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    
    await addressesDB.read();
    const index = addressesDB.data.addresses.findIndex(a => a.id === req.params.id && a.phone === decoded.phone);
    
    if (index === -1) {
      return res.status(404).json({ code: -1, message: '地址不存在' });
    }
    
    addressesDB.data.addresses.splice(index, 1);
    await addressesDB.write();
    
    res.json({ code: 0, data: null });
  } catch (err) {
    res.status(401).json({ code: -1, message: '登录已过期' });
  }
});

// ==================== 裂变系统 API ====================

// 获取或创建用户推荐码
app.post('/api/referral/code', async (req, res) => {
  const { phone } = req.body;
  
  if (!phone) {
    return res.status(400).json({ code: -1, message: '请提供手机号' });
  }
  
  await referralsDB.read();
  
  let referral = referralsDB.data.referrals.find(r => r.phone === phone);
  
  if (!referral) {
    const code = 'RC' + phone.slice(-8) + String(Date.now()).slice(-4);
    referral = {
      id: Date.now().toString(),
      phone,
      code,
      shareCount: 0,
      validInvitations: 0,
      totalRebate: 0,
      created_at: new Date().toISOString()
    };
    referralsDB.data.referrals.push(referral);
    await referralsDB.write();
  }
  
  res.json({ code: 0, data: referral });
});

// 获取用户推荐信息
app.get('/api/referral/info', async (req, res) => {
  const { phone } = req.query;
  
  if (!phone) {
    return res.status(400).json({ code: -1, message: '请提供手机号' });
  }
  
  await referralsDB.read();
  
  const referral = referralsDB.data.referrals.find(r => r.phone === phone);
  
  if (!referral) {
    return res.json({ 
      code: 0, 
      data: { 
        hasReferral: false,
        code: null,
        shareCount: 0,
        validInvitations: 0,
        totalRebate: 0
      } 
    });
  }
  
  res.json({ 
    code: 0, 
    data: { 
      hasReferral: true,
      ...referral
    } 
  });
});

// 分享成功，增加分享次数（发送优惠券）
app.post('/api/referral/share', async (req, res) => {
  const { phone } = req.body;
  
  if (!phone) {
    return res.status(400).json({ code: -1, message: '请提供手机号' });
  }
  
  await referralsDB.read();
  await couponsDB.read();
  
  let referral = referralsDB.data.referrals.find(r => r.phone === phone);
  
  if (!referral) {
    const code = 'RC' + phone.slice(-8) + String(Date.now()).slice(-4);
    referral = {
      id: Date.now().toString(),
      phone,
      code,
      shareCount: 0,
      validInvitations: 0,
      totalRebate: 0,
      created_at: new Date().toISOString()
    };
    referralsDB.data.referrals.push(referral);
  }
  
  referral.shareCount += 1;
  await referralsDB.write();
  
  // 检查是否满足发放优惠券条件（每分享3次得一张优惠券）
  const couponsToGrant = Math.floor(referral.shareCount / 3) - Math.floor((referral.shareCount - 1) / 3);
  
  if (couponsToGrant > 0) {
    for (let i = 0; i < couponsToGrant; i++) {
      couponsDB.data.coupons.push({
        id: Date.now().toString() + i,
        phone,
        type: 'share_reward',
        name: '分享优惠券',
        discount: 20,
        minAmount: 100,
        status: 'unused',
        expireDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        created_at: new Date().toISOString()
      });
    }
    await couponsDB.write();
  }
  
  res.json({ 
    code: 0, 
    data: { 
      message: couponsToGrant > 0 ? `恭喜获得${couponsToGrant}张优惠券！` : '分享成功',
      shareCount: referral.shareCount,
      couponGranted: couponsToGrant
    } 
  });
});

// 使用推荐码（被推荐人下单时绑定）
app.post('/api/referral/bind', async (req, res) => {
  const { myPhone, referrerCode } = req.body;
  
  if (!myPhone || !referrerCode) {
    return res.status(400).json({ code: -1, message: '参数不完整' });
  }
  
  await referralsDB.read();
  
  const referrer = referralsDB.data.referrals.find(r => r.code === referrerCode);
  
  if (!referrer) {
    return res.status(400).json({ code: -1, message: '推荐码无效' });
  }
  
  if (referrer.phone === myPhone) {
    return res.status(400).json({ code: -1, message: '不能推荐自己' });
  }
  
  // 检查是否已经绑定过推荐人
  await couponsDB.read();
  const existingBind = couponsDB.data.coupons.find(c => 
    c.type === 'referral_bind' && c.phone === myPhone && c.referrerPhone === referrer.phone
  );
  
  if (existingBind) {
    return res.status(400).json({ code: -1, message: '已经绑定过推荐码' });
  }
  
  // 给被推荐人发放优惠券
  couponsDB.data.coupons.push({
    id: Date.now().toString(),
    phone: myPhone,
    type: 'referral_bind',
    name: '新用户优惠券',
    discount: 30,
    minAmount: 150,
    status: 'unused',
    expireDate: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    referrerPhone: referrer.phone,
    created_at: new Date().toISOString()
  });
  
  await couponsDB.write();
  
  res.json({ 
    code: 0, 
    data: { 
      message: '绑定成功，获得新用户优惠券！',
      coupon: {
        name: '新用户优惠券',
        discount: 30,
        minAmount: 150
      }
    } 
  });
});

// 订单完成后，给推荐人返利5%
app.post('/api/referral/rebate', async (req, res) => {
  const { orderId } = req.body;
  
  if (!orderId) {
    return res.status(400).json({ code: -1, message: '订单ID不能为空' });
  }
  
  await ordersDB.read();
  await couponsDB.read();
  await rebatesDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === orderId);
  
  if (!order) {
    return res.status(400).json({ code: -1, message: '订单不存在' });
  }
  
  if (order.status !== 'completed') {
    return res.status(400).json({ code: -1, message: '订单未完成，无法返利' });
  }
  
  // 查找该订单是否使用了推荐码
  const coupon = couponsDB.data.coupons.find(c => 
    c.type === 'referral_bind' && c.phone === order.contact_phone
  );
  
  if (!coupon || !coupon.referrerPhone) {
    return res.json({ code: 0, data: { message: '该订单无推荐人，不进行返利' } });
  }
  
  // 检查是否已经返利过
  const existingRebate = rebatesDB.data.rebates.find(r => r.orderId === orderId);
  if (existingRebate) {
    return res.json({ code: 0, data: { message: '该订单已经返利过' } });
  }
  
  // 计算返利金额（订单金额的5%）
  const rebateAmount = Math.round(order.amount * 0.05 * 100) / 100;
  
  // 查找推荐人
  const referral = rebatesDB.data.rebates.find(r => r.phone === coupon.referrerPhone) || 
                   { phone: coupon.referrerPhone, totalRebate: 0, records: [] };
  
  if (!rebatesDB.data.rebates.find(r => r.phone === coupon.referrerPhone)) {
    rebatesDB.data.rebates.push(referral);
  }
  
  // 添加返利记录
  rebatesDB.data.rebates.push({
    id: Date.now().toString(),
    phone: coupon.referrerPhone,
    orderId: orderId,
    orderNo: order.order_no,
    orderAmount: order.amount,
    rebateAmount,
    status: 'available',
    created_at: new Date().toISOString()
  });
  
  referral.totalRebate += rebateAmount;
  await rebatesDB.write();
  
  // 更新推荐人的有效邀请数
  await referralsDB.read();
  const referrerReferral = referralsDB.data.referrals.find(r => r.phone === coupon.referrerPhone);
  if (referrerReferral) {
    referrerReferral.validInvitations += 1;
    referrerReferral.totalRebate += rebateAmount;
    await referralsDB.write();
  }
  
  res.json({ 
    code: 0, 
    data: { 
      message: `返利成功，返利金额：¥${rebateAmount}`,
      rebateAmount
    } 
  });
});

// 获取用户优惠券列表
app.get('/api/coupons', async (req, res) => {
  const { phone, status } = req.query;
  
  if (!phone) {
    return res.status(400).json({ code: -1, message: '请提供手机号' });
  }
  
  await couponsDB.read();
  
  let coupons = couponsDB.data.coupons.filter(c => c.phone === phone);
  
  if (status && status !== 'all') {
    if (status === 'unused') {
      coupons = coupons.filter(c => c.status === 'unused' && c.expireDate >= new Date().toISOString().split('T')[0]);
    } else {
      coupons = coupons.filter(c => c.status === status);
    }
  }
  
  coupons.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  res.json({ code: 0, data: coupons });
});

// 使用优惠券
app.post('/api/coupons/use', async (req, res) => {
  const { couponId } = req.body;
  
  if (!couponId) {
    return res.status(400).json({ code: -1, message: '优惠券ID不能为空' });
  }
  
  await couponsDB.read();
  
  const coupon = couponsDB.data.coupons.find(c => c.id === couponId);
  
  if (!coupon) {
    return res.status(400).json({ code: -1, message: '优惠券不存在' });
  }
  
  if (coupon.status === 'used') {
    return res.status(400).json({ code: -1, message: '优惠券已使用' });
  }
  
  if (coupon.status === 'expired' || coupon.expireDate < new Date().toISOString().split('T')[0]) {
    return res.status(400).json({ code: -1, message: '优惠券已过期' });
  }
  
  coupon.status = 'used';
  coupon.used_at = new Date().toISOString();
  await couponsDB.write();
  
  res.json({ code: 0, data: { message: '优惠券使用成功' } });
});

// 获取返利记录
app.get('/api/rebates', async (req, res) => {
  const { phone } = req.query;
  
  if (!phone) {
    return res.status(400).json({ code: -1, message: '请提供手机号' });
  }
  
  await rebatesDB.read();
  
  const rebates = rebatesDB.data.rebates
    .filter(r => r.phone === phone)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  const totalAvailable = rebates.filter(r => r.status === 'available').reduce((sum, r) => sum + r.rebateAmount, 0);
  
  res.json({ code: 0, data: { rebates, totalAvailable } });
});

// ==================== 产品服务 API ====================

// 获取产品列表
app.get('/api/products', async (req, res) => {
  const { category, includeInactive } = req.query;
  
  await productsDB.read();
  
  let products = productsDB.data.products;
  
  if (category && category !== 'all') {
    products = products.filter(p => p.category === category);
  }
  
  if (!includeInactive || includeInactive !== 'true') {
    products = products.filter(p => !p.status || p.status === 'active');
  }
  
  products.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  res.json({ code: 0, data: products });
});

// 获取单个产品详情
app.get('/api/products/:id', async (req, res) => {
  const { id } = req.params;
  
  await productsDB.read();
  
  const product = productsDB.data.products.find(p => p.id === id);
  
  if (!product) {
    return res.status(404).json({ code: -1, message: '产品不存在' });
  }
  
  res.json({ code: 0, data: product });
});

// 创建产品（管理员）
app.post('/api/admin/products', async (req, res) => {
  const { name, category, price, originalPrice, description, features, image, stock } = req.body;
  
  if (!name || !category || !price) {
    return res.status(400).json({ code: -1, message: '缺少必要参数' });
  }
  
  const product = {
    id: 'product' + String(Date.now()).slice(-6),
    name,
    category,
    price: parseFloat(price),
    originalPrice: parseFloat(originalPrice) || parseFloat(price),
    description: description || '',
    features: features || [],
    image: image || '🖨️',
    stock: parseInt(stock) || 999,
    sales: 0,
    created_at: new Date().toISOString()
  };
  
  await productsDB.read();
  productsDB.data.products.push(product);
  await productsDB.write();
  
  res.json({ code: 0, data: product });
});

// 更新产品（管理员）
app.put('/api/admin/products/:id', async (req, res) => {
  const { id } = req.params;
  const { name, category, price, originalPrice, description, features, image, stock, status } = req.body;
  
  await productsDB.read();
  
  const product = productsDB.data.products.find(p => p.id === id);
  
  if (!product) {
    return res.status(404).json({ code: -1, message: '产品不存在' });
  }
  
  if (name) product.name = name;
  if (category) product.category = category;
  if (price !== undefined) product.price = parseFloat(price);
  if (originalPrice !== undefined) product.originalPrice = parseFloat(originalPrice);
  if (description !== undefined) product.description = description;
  if (features) product.features = features;
  if (image) product.image = image;
  if (stock !== undefined) product.stock = parseInt(stock);
  if (status !== undefined) product.status = status;
  product.updated_at = new Date().toISOString();
  
  await productsDB.write();
  
  res.json({ code: 0, data: product });
});

// 批量更新产品状态（上架/下架）
app.put('/api/admin/products/:id/status', async (req, res) => {
  const { id } = req.params;
  const { status } = req.body;
  
  if (!status || !['active', 'inactive'].includes(status)) {
    return res.status(400).json({ code: -1, message: '状态值无效，应为 active 或 inactive' });
  }
  
  await productsDB.read();
  
  const product = productsDB.data.products.find(p => p.id === id);
  
  if (!product) {
    return res.status(404).json({ code: -1, message: '产品不存在' });
  }
  
  product.status = status;
  product.updated_at = new Date().toISOString();
  
  await productsDB.write();
  
  res.json({ code: 0, data: product });
});

// 删除产品（管理员）
app.delete('/api/admin/products/:id', async (req, res) => {
  const { id } = req.params;
  
  await productsDB.read();
  
  const index = productsDB.data.products.findIndex(p => p.id === id);
  
  if (index === -1) {
    return res.status(404).json({ code: -1, message: '产品不存在' });
  }
  
  productsDB.data.products.splice(index, 1);
  await productsDB.write();
  
  res.json({ code: 0, data: null });
});

// 从商城下单
app.post('/api/orders/buy', async (req, res) => {
  const { productId, quantity, contactName, contactPhone, serviceAddress, remark, couponId } = req.body;
  
  if (!productId || !quantity || !contactName || !contactPhone || !serviceAddress) {
    return res.status(400).json({ code: -1, message: '缺少必要参数' });
  }
  
  await productsDB.read();
  const product = productsDB.data.products.find(p => p.id === productId);
  
  if (!product) {
    return res.status(404).json({ code: -1, message: '产品不存在' });
  }
  
  if (product.stock < quantity) {
    return res.status(400).json({ code: -1, message: '库存不足' });
  }
  
  let totalAmount = product.price * quantity;
  let discount = 0;
  
  if (couponId) {
    await couponsDB.read();
    const coupon = couponsDB.data.coupons.find(c => c.id === couponId);
    
    if (coupon && coupon.status === 'unused' && coupon.expireDate >= new Date().toISOString().split('T')[0]) {
      if (totalAmount >= coupon.minAmount) {
        discount = coupon.discount;
        totalAmount -= discount;
        coupon.status = 'used';
        coupon.used_at = new Date().toISOString();
        await couponsDB.write();
      }
    }
  }
  
  const orderNo = generateOrderNo();
  const order = {
    id: Date.now().toString(),
    order_no: orderNo,
    product_id: productId,
    product_name: product.name,
    product_image: product.image,
    quantity: parseInt(quantity),
    unit_price: product.price,
    amount: totalAmount,
    discount,
    service_type: product.category,
    contact_name: contactName,
    contact_phone: contactPhone,
    service_address: serviceAddress,
    remark: remark || '',
    status: 'pending',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  
  await ordersDB.read();
  ordersDB.data.orders.push(order);
  await ordersDB.write();
  
  product.stock -= quantity;
  product.sales += quantity;
  await productsDB.write();
  
  const payment = {
    timeStamp: Date.now().toString(),
    nonceStr: Math.random().toString(36).substr(2, 15),
    package: 'prepay_id=wx' + Date.now(),
    signType: 'MD5',
    paySign: 'paySign' + Date.now()
  };
  
  res.json({ 
    code: 0, 
    data: { 
      id: order.id, 
      order_no: order.order_no, 
      amount: totalAmount,
      payment: payment
    } 
  });
});

// ==================== 订单状态流转 API ====================

// 确认订单
app.put('/api/admin/orders/:id/confirm', async (req, res) => {
  const { id } = req.params;
  await ordersDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  if (order.status !== 'pending') return res.status(400).json({ code: -1, message: '只能确认待处理订单' });
  
  order.status = 'confirmed';
  order.updated_at = new Date().toISOString();
  order.timeline = order.timeline || [];
  order.timeline.push({
    status: 'confirmed',
    time: new Date().toISOString(),
    operator: '管理员'
  });
  
  await ordersDB.write();
  res.json({ code: 0, data: order });
});

// 分配工程师
app.put('/api/admin/orders/:id/assign', async (req, res) => {
  const { id } = req.params;
  const { engineer_id } = req.body;
  
  if (!engineer_id) return res.status(400).json({ code: -1, message: '请选择工程师' });
  
  await ordersDB.read();
  await engineersDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  
  const engineer = engineersDB.data.engineers.find(e => e.id === engineer_id);
  if (!engineer) return res.status(404).json({ code: -1, message: '工程师不存在' });
  
  order.engineer_id = engineer_id;
  order.engineer_name = engineer.name;
  order.engineer_phone = engineer.phone;
  order.status = 'processing';
  order.updated_at = new Date().toISOString();
  order.timeline = order.timeline || [];
  order.timeline.push({
    status: 'processing',
    time: new Date().toISOString(),
    operator: '管理员',
    remark: `分配给工程师：${engineer.name}`
  });
  
  await ordersDB.write();
  res.json({ code: 0, data: order });
});

// 开始服务
app.put('/api/admin/orders/:id/start', async (req, res) => {
  const { id } = req.params;
  await ordersDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  if (order.status !== 'confirmed') return res.status(400).json({ code: -1, message: '只能开始已确认的订单' });
  
  order.status = 'processing';
  order.service_started_at = new Date().toISOString();
  order.updated_at = new Date().toISOString();
  order.timeline = order.timeline || [];
  order.timeline.push({
    status: 'processing',
    time: new Date().toISOString(),
    operator: order.engineer_name || '工程师'
  });
  
  await ordersDB.write();
  res.json({ code: 0, data: order });
});

// 完成订单
app.put('/api/admin/orders/:id/complete', async (req, res) => {
  const { id } = req.params;
  const { amount, solution, materials } = req.body;
  
  await ordersDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  if (order.status !== 'processing') return res.status(400).json({ code: -1, message: '只能完成服务中的订单' });
  
  order.status = 'completed';
  order.amount = amount || order.amount || 0;
  order.solution = solution || '';
  order.materials = materials || [];
  order.service_completed_at = new Date().toISOString();
  order.updated_at = new Date().toISOString();
  order.timeline = order.timeline || [];
  order.timeline.push({
    status: 'completed',
    time: new Date().toISOString(),
    operator: order.engineer_name || '工程师'
  });
  
  await ordersDB.write();
  res.json({ code: 0, data: order });
});

// 取消订单（管理员）
app.put('/api/admin/orders/:id/cancel', async (req, res) => {
  const { id } = req.params;
  const { reason } = req.body;
  
  await ordersDB.read();
  
  const order = ordersDB.data.orders.find(o => o.id === id);
  if (!order) return res.status(404).json({ code: -1, message: '订单不存在' });
  if (order.status === 'completed' || order.status === 'canceled') {
    return res.status(400).json({ code: -1, message: '已完成或已取消的订单无法取消' });
  }
  
  order.status = 'canceled';
  order.cancel_reason = reason || '';
  order.updated_at = new Date().toISOString();
  order.timeline = order.timeline || [];
  order.timeline.push({
    status: 'canceled',
    time: new Date().toISOString(),
    operator: '管理员',
    remark: reason
  });
  
  await ordersDB.write();
  res.json({ code: 0, data: order });
});

// ==================== 工程师管理 API ====================

// 获取工程师列表
app.get('/api/admin/engineers', async (req, res) => {
  await engineersDB.read();
  res.json({ code: 0, data: engineersDB.data.engineers });
});

// 获取工程师详情
app.get('/api/admin/engineers/:id', async (req, res) => {
  await engineersDB.read();
  const engineer = engineersDB.data.engineers.find(e => e.id === req.params.id);
  if (!engineer) return res.status(404).json({ code: -1, message: '工程师不存在' });
  res.json({ code: 0, data: engineer });
});

// 创建工程师
app.post('/api/admin/engineers', async (req, res) => {
  const { name, phone, email, skills, status } = req.body;
  
  if (!name || !phone) {
    return res.status(400).json({ code: -1, message: '姓名和电话不能为空' });
  }
  
  await engineersDB.read();
  
  const engineer = {
    id: 'ENG' + Date.now().toString().slice(-6),
    name,
    phone,
    email: email || '',
    skills: skills || [],
    status: status || 'active',
    order_count: 0,
    rating: 5.0,
    created_at: new Date().toISOString()
  };
  
  engineersDB.data.engineers.push(engineer);
  await engineersDB.write();
  
  res.json({ code: 0, data: engineer });
});

// 更新工程师
app.put('/api/admin/engineers/:id', async (req, res) => {
  const { name, phone, email, skills, status } = req.body;
  
  await engineersDB.read();
  
  const engineer = engineersDB.data.engineers.find(e => e.id === req.params.id);
  if (!engineer) return res.status(404).json({ code: -1, message: '工程师不存在' });
  
  if (name) engineer.name = name;
  if (phone) engineer.phone = phone;
  if (email !== undefined) engineer.email = email;
  if (skills) engineer.skills = skills;
  if (status) engineer.status = status;
  engineer.updated_at = new Date().toISOString();
  
  await engineersDB.write();
  res.json({ code: 0, data: engineer });
});

// 删除工程师
app.delete('/api/admin/engineers/:id', async (req, res) => {
  await engineersDB.read();
  
  const index = engineersDB.data.engineers.findIndex(e => e.id === req.params.id);
  if (index === -1) return res.status(404).json({ code: -1, message: '工程师不存在' });
  
  engineersDB.data.engineers.splice(index, 1);
  await engineersDB.write();
  
  res.json({ code: 0, data: null });
});

// 获取工程师统计
app.get('/api/admin/engineers/:id/stats', async (req, res) => {
  await engineersDB.read();
  await ordersDB.read();
  
  const engineer = engineersDB.data.engineers.find(e => e.id === req.params.id);
  if (!engineer) return res.status(404).json({ code: -1, message: '工程师不存在' });
  
  const engineerOrders = ordersDB.data.orders.filter(o => o.engineer_id === req.params.id);
  const completedOrders = engineerOrders.filter(o => o.status === 'completed');
  const totalAmount = completedOrders.reduce((sum, o) => sum + (o.amount || 0), 0);
  
  res.json({
    code: 0,
    data: {
      total_orders: engineerOrders.length,
      completed_orders: completedOrders.length,
      processing_orders: engineerOrders.filter(o => o.status === 'processing').length,
      total_amount: totalAmount,
      rating: engineer.rating
    }
  });
});

// ==================== 客户管理 API ====================

// 获取客户列表
app.get('/api/admin/customers', async (req, res) => {
  await ordersDB.read();
  
  const customerMap = new Map();
  ordersDB.data.orders.forEach(order => {
    const phone = order.contact_phone;
    if (!customerMap.has(phone)) {
      customerMap.set(phone, {
        phone,
        name: order.contact_name,
        order_count: 0,
        total_amount: 0,
        last_order_time: order.created_at
      });
    }
    const customer = customerMap.get(phone);
    customer.order_count++;
    customer.total_amount += order.amount || 0;
    if (new Date(order.created_at) > new Date(customer.last_order_time)) {
      customer.last_order_time = order.created_at;
    }
  });
  
  const customers = Array.from(customerMap.values()).sort((a, b) => 
    new Date(b.last_order_time) - new Date(a.last_order_time)
  );
  
  res.json({ code: 0, data: customers });
});

// 获取客户详情
app.get('/api/admin/customers/:phone', async (req, res) => {
  await ordersDB.read();
  
  const phone = req.params.phone;
  const customerOrders = ordersDB.data.orders.filter(o => o.contact_phone === phone);
  
  if (customerOrders.length === 0) {
    return res.status(404).json({ code: -1, message: '客户不存在' });
  }
  
  const customer = {
    phone,
    name: customerOrders[0].contact_name,
    orders: customerOrders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  };
  
  res.json({ code: 0, data: customer });
});

// ==================== 数据统计 API ====================

// 获取统计数据
app.get('/api/admin/stats', async (req, res) => {
  await ordersDB.read();
  await engineersDB.read();
  
  const orders = ordersDB.data.orders;
  const today = new Date().toISOString().split('T')[0];
  const todayOrders = orders.filter(o => o.created_at.startsWith(today));
  
  const stats = {
    total: orders.length,
    today: todayOrders.length,
    pending: orders.filter(o => o.status === 'pending').length,
    confirmed: orders.filter(o => o.status === 'confirmed').length,
    processing: orders.filter(o => o.status === 'processing').length,
    completed: orders.filter(o => o.status === 'completed').length,
    canceled: orders.filter(o => o.status === 'canceled').length,
    total_amount: orders.filter(o => o.status === 'completed').reduce((sum, o) => sum + (o.amount || 0), 0),
    today_amount: todayOrders.filter(o => o.status === 'completed').reduce((sum, o) => sum + (o.amount || 0), 0),
    engineer_count: engineersDB.data.engineers.length,
    active_engineer_count: engineersDB.data.engineers.filter(e => e.status === 'active').length
  };
  
  res.json({ code: 0, data: stats });
});

// 获取订单趋势（最近7天）
app.get('/api/admin/stats/trend', async (req, res) => {
  await ordersDB.read();
  
  const days = 7;
  const trend = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    
    const dayOrders = ordersDB.data.orders.filter(o => o.created_at.startsWith(dateStr));
    
    trend.push({
      date: dateStr,
      total: dayOrders.length,
      completed: dayOrders.filter(o => o.status === 'completed').length,
      amount: dayOrders.filter(o => o.status === 'completed').reduce((sum, o) => sum + (o.amount || 0), 0)
    });
  }
  
  res.json({ code: 0, data: trend });
});

// 获取服务类型分布
app.get('/api/admin/stats/service-types', async (req, res) => {
  await ordersDB.read();
  
  const typeCount = {};
  ordersDB.data.orders.forEach(order => {
    const type = order.service_type || 'other';
    typeCount[type] = (typeCount[type] || 0) + 1;
  });
  
  const typeMap = {
    repair: '维修服务',
    rent: '设备租赁',
    supplies: '耗材配件',
    sale: '设备购买',
    other: '其他'
  };
  
  const data = Object.entries(typeCount).map(([type, count]) => ({
    type,
    name: typeMap[type] || type,
    count
  }));
  
  res.json({ code: 0, data });
});

// 获取工程师工作量排行
app.get('/api/admin/stats/engineers', async (req, res) => {
  await ordersDB.read();
  await engineersDB.read();
  
  const engineerStats = engineersDB.data.engineers.map(engineer => {
    const orders = ordersDB.data.orders.filter(o => o.engineer_id === engineer.id);
    const completed = orders.filter(o => o.status === 'completed');
    
    return {
      id: engineer.id,
      name: engineer.name,
      total_orders: orders.length,
      completed_orders: completed.length,
      total_amount: completed.reduce((sum, o) => sum + (o.amount || 0), 0),
      status: engineer.status
    };
  }).sort((a, b) => b.completed_orders - a.completed_orders);
  
  res.json({ code: 0, data: engineerStats });
});

// ==================== 全局错误处理中间件 ====================
app.use((err, req, res, next) => {
  console.error('服务器错误:', err);
  
  if (err.name === 'JsonWebTokenError') {
    return res.status(401).json({ code: -1, message: '无效的登录凭证' });
  }
  
  if (err.name === 'TokenExpiredError') {
    return res.status(401).json({ code: -1, message: '登录已过期，请重新登录' });
  }
  
  if (err.code === 'ENOENT') {
    return res.status(500).json({ code: -1, message: '文件不存在' });
  }
  
  res.status(500).json({ code: -1, message: '服务器内部错误，请稍后重试' });
});

// ==================== 评价 API ====================

// 获取商品评价列表（已审核）
app.get('/api/reviews/product/:productId', async (req, res) => {
  const { productId } = req.params;
  
  await reviewsDB.read();
  const reviews = reviewsDB.data.reviews.filter(r => r.productId === productId && r.status === 'approved');
  reviews.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  res.json({ code: 0, data: reviews });
});

// 获取商品评价统计
app.get('/api/reviews/product/:productId/stats', async (req, res) => {
  const { productId } = req.params;
  
  await reviewsDB.read();
  const productReviews = reviewsDB.data.reviews.filter(r => r.productId === productId && r.status === 'approved');
  
  const stats = {
    total: productReviews.length
  };
  
  res.json({ code: 0, data: stats });
});

// 提交评价
app.post('/api/reviews', async (req, res) => {
  const { orderId, productId, content, images } = req.body;
  
  if (!orderId || !productId || !content) {
    return res.status(400).json({ code: -1, message: '缺少必要参数' });
  }
  
  await ordersDB.read();
  const order = ordersDB.data.orders.find(o => o.id === orderId);
  if (!order) {
    return res.status(404).json({ code: -1, message: '订单不存在' });
  }
  
  if (order.status !== 'completed') {
    return res.status(400).json({ code: -1, message: '只能对已完成的订单进行评价' });
  }
  
  await reviewsDB.read();
  const existingReview = reviewsDB.data.reviews.find(r => r.orderId === orderId);
  if (existingReview) {
    return res.status(400).json({ code: -1, message: '该订单已评价过' });
  }
  
  const review = {
    id: 'review' + Date.now(),
    productId: productId,
    orderId: orderId,
    userId: order.contact_phone || 'unknown',
    userName: order.contact_name || '用户',
    userPhone: order.contact_phone ? order.contact_phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '',
    content: content,
    images: images || [],
    status: 'pending',
    created_at: new Date().toISOString()
  };
  
  reviewsDB.data.reviews.push(review);
  await reviewsDB.write();
  
  res.json({ code: 0, data: { id: review.id, message: '评价提交成功，等待审核' } });
});

// 管理员获取待审核评价
app.get('/api/admin/reviews/pending', async (req, res) => {
  await reviewsDB.read();
  const pendingReviews = reviewsDB.data.reviews.filter(r => r.status === 'pending');
  pendingReviews.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  
  res.json({ code: 0, data: pendingReviews });
});

// 管理员审核评价
app.put('/api/admin/reviews/:id/approve', async (req, res) => {
  const { id } = req.params;
  
  await reviewsDB.read();
  const review = reviewsDB.data.reviews.find(r => r.id === id);
  if (!review) {
    return res.status(404).json({ code: -1, message: '评价不存在' });
  }
  
  review.status = 'approved';
  review.approved_at = new Date().toISOString();
  await reviewsDB.write();
  
  res.json({ code: 0, data: review });
});

// 管理员拒绝评价
app.put('/api/admin/reviews/:id/reject', async (req, res) => {
  const { id } = req.params;
  
  await reviewsDB.read();
  const review = reviewsDB.data.reviews.find(r => r.id === id);
  if (!review) {
    return res.status(404).json({ code: -1, message: '评价不存在' });
  }
  
  review.status = 'rejected';
  review.rejected_at = new Date().toISOString();
  await reviewsDB.write();
  
  res.json({ code: 0, data: review });
});

// 获取评价详情
app.get('/api/reviews/:id', async (req, res) => {
  const { id } = req.params;
  
  await reviewsDB.read();
  const review = reviewsDB.data.reviews.find(r => r.id === id);
  if (!review) {
    return res.status(404).json({ code: -1, message: '评价不存在' });
  }
  
  res.json({ code: 0, data: review });
});

// ==================== 用户登录相关 ====================

// 获取用户openid（通过wx.login的code换取）
app.post('/api/user/getOpenid', async (req, res) => {
  const { code } = req.body;
  
  if (!code) {
    return res.status(400).json({ code: -1, message: 'code不能为空' });
  }
  
  try {
    const axios = require('axios');
    
    // 小程序的AppID和AppSecret
    const appId = '<REDACTED:wx-appid>';
    const appSecret = '<REDACTED:wx-appsecret>'; // 请替换为你的AppSecret
    
    // 调用微信code2Session接口
    const response = await axios.get(
      `https://api.weixin.qq.com/sns/jscode2session?appid=${appId}&secret=${appSecret}&js_code=${code}&grant_type=authorization_code`,
      { timeout: 10000 }
    );
    
    const data = response.data;
    
    if (data.errcode) {
      console.error('获取openid失败:', data);
      return res.status(400).json({ code: -1, message: data.errmsg || '获取openid失败' });
    }
    
    res.json({ 
      code: 0, 
      data: { 
        openid: data.openid,
        session_key: data.session_key
      } 
    });
  } catch (error) {
    console.error('获取openid失败:', error);
    res.status(500).json({ code: -1, message: '获取openid失败' });
  }
});

// ==================== 微信支付 API ====================

// 引入微信支付工具（如果依赖未安装，会报错）
let wxpayUtils = null;
try {
  wxpayUtils = require('./wxpay-utils');
} catch (e) {
  console.log('微信支付工具加载失败，请确保已安装 xml2js 和 axios 依赖');
}

// 商品订单数据库（用于存储商品租赁订单）
const productOrdersDB = {
  data: { orders: [] },
  read: async function() {
    const fs = require('fs');
    const path = require('path');
    const dbPath = path.join(__dirname, 'data', 'product-orders.json');
    try {
      if (fs.existsSync(dbPath)) {
        const data = fs.readFileSync(dbPath, 'utf8');
        this.data = JSON.parse(data);
      } else {
        this.data = { orders: [] };
        fs.writeFileSync(dbPath, JSON.stringify(this.data, null, 2));
      }
    } catch (e) {
      this.data = { orders: [] };
    }
  },
  write: async function() {
    const fs = require('fs');
    const path = require('path');
    const dbPath = path.join(__dirname, 'data', 'product-orders.json');
    fs.writeFileSync(dbPath, JSON.stringify(this.data, null, 2));
  }
};

// 创建商品租赁订单并发起支付
app.post('/api/wxpay/create-order', async (req, res) => {
  if (!wxpayUtils) {
    return res.status(500).json({ code: -1, message: '微信支付功能未配置' });
  }
  
  const { items, totalAmount, contactName, contactPhone, serviceAddress, openid } = req.body;
  
  if (!items || !items.length || !totalAmount || !openid) {
    return res.status(400).json({ code: -1, message: '参数不完整' });
  }
  
  try {
    // 生成商户订单号
    const outTradeNo = wxpayUtils.generateOutTradeNo();
    
    // 创建商品订单
    const order = {
      id: Date.now().toString(),
      order_no: outTradeNo,
      items: items,
      total_amount: totalAmount,
      contact_name: contactName || '',
      contact_phone: contactPhone || '',
      service_address: serviceAddress || '',
      openid: openid,
      status: 'pending',
      created_at: new Date().toISOString()
    };
    
    // 保存订单
    await productOrdersDB.read();
    productOrdersDB.data.orders.push(order);
    await productOrdersDB.write();
    
    // 调用微信统一下单
    const wxOrder = await wxpayUtils.unifiedOrder({
      body: `商品租赁-${items.length}件商品`,
      out_trade_no: outTradeNo,
      total_fee: Math.round(totalAmount * 100), // 元转分
      openid: openid,
      spbill_create_ip: req.ip || '127.0.0.1'
    });
    
    // 生成支付参数
    const payParams = wxpayUtils.generatePayParams(wxOrder.prepay_id);
    
    res.json({ 
      code: 0, 
      data: {
        orderId: order.id,
        orderNo: outTradeNo,
        ...payParams
      } 
    });
  } catch (error) {
    console.error('创建支付订单失败:', error);
    res.status(500).json({ code: -1, message: error.message || '创建订单失败' });
  }
});

// 微信支付回调
app.post('/api/wxpay/callback', async (req, res) => {
  if (!wxpayUtils) {
    return res.send(wxpayUtils.buildXML({ return_code: 'FAIL', return_msg: '系统错误' }));
  }
  
  try {
    // 解析XML
    const xmlData = req.body;
    const params = await wxpayUtils.parseXML(xmlData);
    
    console.log('微信支付回调:', params);
    
    // 验证签名
    const wxpayConfig = require('./wxpay-config');
    if (!wxpayUtils.verifySign(params, wxpayConfig.apiKey)) {
      return res.send(wxpayUtils.buildXML({ return_code: 'FAIL', return_msg: '签名错误' }));
    }
    
    // 处理支付结果
    if (params.result_code === 'SUCCESS') {
      // 更新订单状态
      await productOrdersDB.read();
      const order = productOrdersDB.data.orders.find(o => o.order_no === params.out_trade_no);
      if (order) {
        order.status = 'paid';
        order.transaction_id = params.transaction_id;
        order.paid_at = new Date().toISOString();
        await productOrdersDB.write();
      }
      
      res.send(wxpayUtils.buildXML({ return_code: 'SUCCESS', return_msg: 'OK' }));
    } else {
      res.send(wxpayUtils.buildXML({ return_code: 'FAIL', return_msg: params.err_code_des || '支付失败' }));
    }
  } catch (error) {
    console.error('处理支付回调失败:', error);
    res.send(wxpayUtils.buildXML({ return_code: 'FAIL', return_msg: '处理失败' }));
  }
});

// 查询订单状态
app.get('/api/wxpay/order/:orderNo', async (req, res) => {
  if (!wxpayUtils) {
    return res.status(500).json({ code: -1, message: '微信支付功能未配置' });
  }
  
  const { orderNo } = req.params;
  
  try {
    // 查询本地订单
    await productOrdersDB.read();
    const order = productOrdersDB.data.orders.find(o => o.order_no === orderNo);
    
    if (!order) {
      return res.status(404).json({ code: -1, message: '订单不存在' });
    }
    
    // 如果订单待支付，查询微信订单状态
    if (order.status === 'pending') {
      const wxResult = await wxpayUtils.queryOrder(orderNo);
      if (wxResult.trade_state === 'SUCCESS') {
        order.status = 'paid';
        order.transaction_id = wxResult.transaction_id;
        order.paid_at = new Date().toISOString();
        await productOrdersDB.write();
      }
    }
    
    res.json({ code: 0, data: order });
  } catch (error) {
    console.error('查询订单失败:', error);
    res.status(500).json({ code: -1, message: '查询订单失败' });
  }
});

// 获取用户的商品订单列表
app.get('/api/product-orders', async (req, res) => {
  const { openid } = req.query;
  
  await productOrdersDB.read();
  let orders = productOrdersDB.data.orders;
  
  if (openid) {
    orders = orders.filter(o => o.openid === openid);
  }
  
  orders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  res.json({ code: 0, data: orders });
});

// 404 处理
app.use((req, res) => {
  res.status(404).json({ code: -1, message: '请求的资源不存在' });
});

initDatabase().then(() => {
  app.listen(PORT, () => {
    console.log(`后端服务运行在 http://localhost:${PORT}`);
    console.log('管理员账号: admin / admin123');
    console.log('API文档:');
    console.log('  POST /api/login - 管理员登录');
    console.log('  GET  /api/orders - 获取订单列表');
    console.log('  GET  /api/orders/:id - 获取订单详情');
    console.log('  POST /api/orders - 创建订单');
    console.log('  PUT  /api/admin/orders/:id/confirm - 确认订单');
    console.log('  PUT  /api/admin/orders/:id/assign - 分配工程师');
    console.log('  PUT  /api/admin/orders/:id/start - 开始服务');
    console.log('  PUT  /api/admin/orders/:id/complete - 完成订单');
    console.log('  PUT  /api/admin/orders/:id/cancel - 取消订单');
    console.log('  GET  /api/admin/engineers - 获取工程师列表');
    console.log('  POST /api/admin/engineers - 创建工程师');
    console.log('  PUT  /api/admin/engineers/:id - 更新工程师');
    console.log('  DEL  /api/admin/engineers/:id - 删除工程师');
    console.log('  GET  /api/admin/customers - 获取客户列表');
    console.log('  GET  /api/admin/stats - 统计数据');
    console.log('  GET  /api/admin/stats/trend - 订单趋势');
    console.log('  GET  /api/admin/stats/service-types - 服务类型分布');
    console.log('  GET  /api/admin/stats/engineers - 工程师排行');
  });
});