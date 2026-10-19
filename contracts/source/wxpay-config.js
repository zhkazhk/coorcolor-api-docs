/**
 * 微信支付配置
 * 注意：API密钥需要妥善保管，不要提交到公开仓库
 */

const wxpayConfig = {
  // 小程序AppID
  appId: '<REDACTED:wx-appid>',
  
  // 商户号
  mchId: '<REDACTED:wxpay-mchid>',
  
  // API密钥（32位，需要在微信商户平台设置）
  apiKey: '<REDACTED:wxpay-apikey>',
  
  // 支付回调地址（需要修改为你的实际域名）
  notifyUrl: '<REDACTED:notify-url>',
  
  // 签名类型
  signType: 'MD5'
};

module.exports = wxpayConfig;
