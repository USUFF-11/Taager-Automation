import requests

TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7Il9pZCI6IjY4NmU5MDYxOTk3ZTg5MThjY2VkYzhiNiIsImVtYWlsIjoieW91c3NlZmVsc2hheWViMTAwQGdtYWlsLmNvbSIsIlRhZ2VySUQiOjE5MDk5MTMsInVzZXJMZXZlbCI6MSwidXNlcm5hbWUiOiJ5b3Vzc2VmZWxzaGF5ZWIxMDBAZ21haWwuY29tIiwicGhvbmVOdW1iZXIiOnsiX3ZhbHVlIjoiMjAxMTU0MDc5OTI2IiwiX2NhbGxpbmdDb2RlIjoiMjAifSwidmVyaWZpY2F0aW9uU3RhdGUiOnsicGhvbmVOdW1iZXJWZXJpZmllZCI6dHJ1ZSwibWVyY2hhbnREYXRhVmVyaWZpZWQiOnRydWUsImVtYWlsVmVyaWZpZWQiOnRydWUsIm1lcmNoYW50SWRWZXJpZmllZCI6ZmFsc2V9LCJhY3R1YWxWZXJpZmljYXRpb25TdGF0ZSI6eyJyZWdpc3RyYXRpb25Db21wbGV0ZWQiOnRydWUsInBob25lTnVtYmVyVmVyaWZpZWQiOnRydWUsIm1lcmNoYW50RGF0YVZlcmlmaWVkIjp0cnVlLCJlbWFpbFZlcmlmaWVkIjp0cnVlLCJtZXJjaGFudElkVmVyaWZpZWQiOmZhbHNlfSwic3RvcmVzIjpbXSwiZmVhdHVyZXMiOlsiYnJlYWtfZXZlbl9tZXJjaGFudF9pbnNpZ2h0cyIsImJ1bGtfcHJlb3JkZXJfZXhwZXJpbWVudCIsImNwYV9jYWxjdWxhdG9yIiwiZHVrYW5fYXJlIiwiZHVrYW5fZWd5IiwiZHVrYW5faXJxIiwiZHVrYW5fdG10IiwiZHVrYW5fdjIiLCJkeW5hbWljX2luY2VudGl2ZV9wcm9ncmFtIiwiZHluYW1pY19wcmljaW5nX2VneSIsImZhaWxlZF9vcmRlcnMiLCJmdW5kaW5nLXJlcXVlc3QtYXV0b21hdGlvbi1pbmNsdWRlZCIsImt5YyIsImxveWFsdHlfcHJvZ3JhbSIsIm1hcmtldC1wbGFjZS1ub3RpZmljYXRpb25zLWxvY2stdXBkYXRlcyIsIm1lcmNoYW50X2luc2lnaHRzIiwibWlzc2VkX29yZGVycyIsIm11bHRpdGVuYW5jeSIsIm11bHRpdGVuYW5jeV9pcmFxIiwibXVsdGl0ZW5hbmN5X29tYW4iLCJtdWx0aXRlbmFuY3lfdWFlIiwicHJlb3JkZXJfc2F1IiwicmVmZXJyYWxfcHJvZ3JhbSIsInNob3dfYWRzX3Byb2ZpdF9pbnNpZ2h0cyIsInNrdV9hbmFseXRpY3NfYXJlIiwic2t1X2FuYWx5dGljc19lZ3kiLCJza3VfYW5hbHl0aWNzX3NhdSIsInN0b2NrX2F2YWlsYWJpbGl0eV9lZ3kiLCJzdG9ja19hdmFpbGFiaWxpdHlfc2F1Iiwic3RvcmVzX3JldmFtcCIsIndlYl9uZXdfaG9tZXBhZ2UiLCJ3ZWJfbmV3X21lcmNoYW50X2xheW91dCIsIndpdGhkcmF3YWxfb3RwIiwid29vX2NvbW1lcmNlX3N0b3JlIiwieW91Y2FuX2FyZSIsInlvdWNhbl9lZ3kiLCJ5b3VjYW5fc2F1Il19LCJpYXQiOjE3ODI5NDk3NzIsImV4cCI6MTc4MzAzNjE3Mn0.ulD2Pr3owqDHWUgPZ3aO85QqS9cy1hfgtNiLn88JmSo"

url = "https://merchant.api.taager.com/api/products/variants"

headers = {
    "Authorization": TOKEN,
    "country": "EGY",
    "platform": "web",
    "accept": "application/json",
}

params = {
    "page": 1,
    "pageSize": 25,
    "sortBy": "introducedAt",
    "sortOrder": "descending"
    # لاحظ: مفيش categoryId
}

response = requests.get(url, headers=headers, params=params)

print("Status Code:", response.status_code)

if response.status_code == 200:

    products = response.json()

    print("Products:", len(products))
    print("-" * 50)

    for product in products:
        print(
            product["productId"],
            "|",
            product["name"]
        )

else:
    print(response.text)