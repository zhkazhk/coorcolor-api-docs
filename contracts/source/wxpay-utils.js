/**
 * 微信支付工具函数（不依赖外部库）
 */

const crypto = require('crypto');
const https = require('https');

// 微信支付配置
const wxpayConfig = require('./wxpay-config');

/**
 * 生成随机字符串
 */
function generateNonceStr(length = 32) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 * 生成签名
 */
function generateSign(params, key) {
  const sortedKeys = Object.keys(params).sort();
  
  const stringA = sortedKeys
    .filter(key => params[key] !== '' && params[key] !== undefined && params[key] !== null)
    .map(key => `${key}=${params[key]}`)
    .join('&');
  
  const stringSignTemp = `${stringA}&key=${key}`;
  
  return crypto.createHash('md5').update(stringSignTemp, 'utf8').digest('hex').toUpperCase();
}

/**
 * 验证签名
 */
function verifySign(params, key) {
  const { sign, ...rest } = params;
  const calculatedSign = generateSign(rest, key);
  return sign === calculatedSign;
}

/**
 * 对象转XML
 */
function buildXML(obj) {
  let xml = '<xml>';
  for (const key in obj) {
    const value = obj[key];
    xml += `<${key}><![CDATA[${value}]]></${key}>`;
  }
  xml += '</xml>';
  return xml;
}

/**
 * XML转对象（简单实现）
 */
function parseXML(xml) {
  const result = {};
  const regex = /<(\w+)><!\[CDATA\[([^\]]+)\]\]><\/\w+>/g;
  let match;
  
  while ((match = regex.exec(xml)) !== null) {
    result[match[1]] = match[2];
  }
  
  return result;
}

/**
 * 生成商户订单号
 */
function generateOutTradeNo() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hour = String(now.getHours()).padStart(2, '0');
  const minute = String(now.getMinutes()).padStart(2, '0');
  const second = String(now.getSeconds()).padStart(2, '0');
  const random = String(Math.floor(Math.random() * 10000)).padStart(4, '0');
  return `WX${year}${month}${day}${hour}${minute}${second}${random}`;
}

/**
 * HTTPS POST请求
 */
function httpsPost(url, data, timeout = 10000) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/xml',
        'Content-Length': Buffer.byteLength(data)
      },
      timeout: timeout
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => {
        body += chunk.toString('utf8');
      });
      res.on('end', () => {
        resolve(body);
      });
    });
    
    req.on('error', (err) => {
      reject(err);
    });
    
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('请求超时'));
    });
    
    req.write(data);
    req.end();
  });
}

/**
 * 统一下单
 */
async function unifiedOrder(orderData) {
  const params = {
    appid: wxpayConfig.appId,
    mch_id: wxpayConfig.mchId,
    nonce_str: generateNonceStr(),
    body: orderData.body,
    out_trade_no: orderData.out_trade_no,
    total_fee: orderData.total_fee,
    spbill_create_ip: orderData.spbill_create_ip || '127.0.0.1',
    notify_url: wxpayConfig.notifyUrl,
    trade_type: 'JSAPI',
    openid: orderData.openid
  };
  
  params.sign = generateSign(params, wxpayConfig.apiKey);
  
  const xml = buildXML(params);
  
  try {
    const response = await httpsPost('https://api.mch.weixin.qq.com/pay/unifiedorder', xml);
    const result = parseXML(response);
    
    if (result.return_code !== 'SUCCESS') {
      throw new Error(result.return_msg || '统一下单失败');
    }
    
    if (result.result_code !== 'SUCCESS') {
      throw new Error(result.err_code_des || '统一下单失败');
    }
    
    return result;
  } catch (error) {
    console.error('统一下单失败:', error);
    throw error;
  }
}

/**
 * 生成小程序支付参数
 */
function generatePayParams(prepayId) {
  const params = {
    appId: wxpayConfig.appId,
    timeStamp: String(Math.floor(Date.now() / 1000)),
    nonceStr: generateNonceStr(),
    package: `prepay_id=${prepayId}`,
    signType: wxpayConfig.signType
  };
  
  params.paySign = generateSign(params, wxpayConfig.apiKey);
  
  return {
    timeStamp: params.timeStamp,
    nonceStr: params.nonceStr,
    package: params.package,
    signType: params.signType,
    paySign: params.paySign
  };
}

/**
 * 查询订单
 */
async function queryOrder(outTradeNo) {
  const params = {
    appid: wxpayConfig.appId,
    mch_id: wxpayConfig.mchId,
    out_trade_no: outTradeNo,
    nonce_str: generateNonceStr()
  };
  
  params.sign = generateSign(params, wxpayConfig.apiKey);
  
  const xml = buildXML(params);
  
  const response = await httpsPost('https://api.mch.weixin.qq.com/pay/orderquery', xml);
  const result = parseXML(response);
  
  return result;
}

module.exports = {
  generateNonceStr,
  generateSign,
  verifySign,
  buildXML,
  parseXML,
  generateOutTradeNo,
  unifiedOrder,
  generatePayParams,
  queryOrder
};
