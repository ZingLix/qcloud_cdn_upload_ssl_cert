import requests
import os
import hashlib
import hmac
import json
import time
from datetime import datetime

# 腾讯云密钥
TENCENT_SECRET_ID = os.environ["TENCENT_SECRET_ID"]
TENCENT_SECRET_KEY = os.environ["TENCENT_SECRET_KEY"]
# ACME 域名名称
SSL_DOMAIN = os.environ["SSL_DOMAIN"]
# 腾讯云 CDN 名称，多个之间用,分割
CDN_DOMAIN = os.environ["CDN_DOMAIN"]
# 证书是否 ECC，区别在 ACME 证书路径会有 _ecc 后缀，不设置则没有
ECC_CERT = os.environ.get("ECC_CERT", False)
# 证书存放路径，不用加具体域名
CERT_PATH = os.environ["CERT_PATH"]

cert_path = f"{CERT_PATH}/{SSL_DOMAIN}{'' if ECC_CERT is False else '_ecc'}"
public_key = f"{cert_path}/fullchain.cer"
private_key = f"{cert_path}/{SSL_DOMAIN}.key"

with open(public_key, "r") as f:
    public_key_content = f.read()

with open(private_key, "r") as f:
    private_key_content = f.read()


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def request(
    action, body, version="2019-12-05", service="ssl", host="ssl.tencentcloudapi.com"
):
    region = ""
    endpoint = f"https://{host}"
    algorithm = "TC3-HMAC-SHA256"
    payload = json.dumps(body)
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    # ************* 步骤 1：拼接规范请求串 *************
    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    ct = "application/json; charset=utf-8"
    canonical_headers = "content-type:%s\nhost:%s\nx-tc-action:%s\n" % (
        ct,
        host,
        action.lower(),
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = (
        http_request_method
        + "\n"
        + canonical_uri
        + "\n"
        + canonical_querystring
        + "\n"
        + canonical_headers
        + "\n"
        + signed_headers
        + "\n"
        + hashed_request_payload
    )

    # ************* 步骤 2：拼接待签名字符串 *************
    credential_scope = date + "/" + service + "/" + "tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")
    ).hexdigest()
    string_to_sign = (
        algorithm
        + "\n"
        + str(timestamp)
        + "\n"
        + credential_scope
        + "\n"
        + hashed_canonical_request
    )

    # ************* 步骤 3：计算签名 *************
    secret_date = sign(("TC3" + TENCENT_SECRET_KEY).encode("utf-8"), date)
    secret_service = sign(secret_date, service)
    secret_signing = sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # ************* 步骤 4：拼接 Authorization *************
    authorization = (
        algorithm
        + " "
        + "Credential="
        + TENCENT_SECRET_ID
        + "/"
        + credential_scope
        + ", "
        + "SignedHeaders="
        + signed_headers
        + ", "
        + "Signature="
        + signature
    )

    # ************* 步骤 5：构造并发起请求 *************
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
    }
    r = requests.post(endpoint, headers=headers, json=body)
    return r.json()


# upload certificate
resp = request(
    "UploadCertificate",
    {
        "CertificatePublicKey": public_key_content,
        "CertificatePrivateKey": private_key_content,
        "CertificateType": "SVR",
        "Alias": f"{SSL_DOMAIN}_{int(time.time())}",
        "CertificateUse": "CDN",
        "Repeatable": False,
    },
)

cert_id = resp["Response"]["CertificateId"]
if "Error" in resp['Response']:
    print(f"Upload SSL certificate failed! Error: {resp['Response']['Error']['Code']}")
    os._exit(-1)
print(f"Cert upload success, cert id: {cert_id}")

cdn_domain_list = CDN_DOMAIN.split(",")
for domain in cdn_domain_list:
    resp = request(
        "ModifyDomainConfig",
        {
            "Domain": domain,
            "Route": "Https.CertInfo.CertId",
            "Value": json.dumps({
                "update": cert_id
            }),
        },
        service="cdn",
        version="2018-06-06",
        host="cdn.tencentcloudapi.com",
    )
    if "Error" in resp['Response']:
        print(f"Deploy {domain} failed! Error: {resp['Response']['Error']['Code']}")
    else:
        print(f"Deploy {domain} success")
