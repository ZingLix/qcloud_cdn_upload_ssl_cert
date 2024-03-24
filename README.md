# 腾讯云证书自动上传 & CDN 部署

鉴于腾讯云不再提供一年证书，而三个月有效期又需要频繁手动更新过于麻烦，腾讯云也不提供自动更新证书

所以写了个脚本，可以自动将本地 ACME 证书上传至腾讯云，并且部署至 CDN

**使用方法**：

通过环境变量进行设置，假设证书位于 `/root/.acme.sh/example.com`，该目录下应该有 `fullchain.cer`、`example.com.key` 这类文件，那么就按如下方式设置：

```shell
# 腾讯云密钥，从 https://console.cloud.tencent.com/cam/capi 获取
export TENCENT_SECRET_ID=xxx
export TENCENT_SECRET_KEY=xxx
# SSL 证书的域名
export SSL_DOMAIN="example.com"
# 腾讯云 CDN 待部署的域名，多个域名用 , 分隔
export CDN_DOMAIN="example.com,blog.example.com"
# 是否 ECC 证书，区别在于证书路径上会有 _ecc 后缀，如果不是 ECC 证书不设置该变量即可
export ECC_CERT=1
# 证书存放路径
export CERT_PATH=/root/.acme.sh

python upload.py
```

配合 ACME 自动更新证书，定时运行该脚本即可
