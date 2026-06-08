import nest_asyncio
nest_asyncio.apply()
import asyncio
import json
import os
import smtplib
import requests  # 👈 追加①
from email.mime.text import MIMEText
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def main():
    # 👈 追加②：始まった瞬間にLINEへ「作動」とだけ送る
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LINE_MESSEGE_API')}"
        },
        json={
            "to": os.environ.get("LINE_USER_ID"),
            "messages": [{"type": "text", "text": "テニスボット作動"}]
        }
    )

    async with async_playwright() as p:
        # 💡 本番（GitHub）は画面がないので、headless=True にします
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print("1. トップページを開きます...")
            await page.goto("https://resv.city.meguro.tokyo.jp/Web/Home/WgR_ModeSelect")

            print("2. 「使用目的から探す」をクリックします...")
            await page.locator("text=使用目的から探す").click()

            print("3. 「硬式テニス」を選択します...")
            await page.locator("text=硬式テニス").click()
            await page.get_by_role("button",name="検索").click()

            print("4. 施設を4つ選択します...")
            await page.locator("text=駒場体育館").first.click()
            await page.locator("text=区民センター体育館").first.click()
            await page.locator("text=碑文谷体育館").first.click()
            await page.locator("text=宮前公園庭球場").first.click()

            print("5. 「次へ進む」をクリックします...")
            await page.locator("text=次へ進む").nth(1).click() 

            print("6. 「その他条件で絞り込む」をクリック...")
            await page.locator("text=その他の条件で絞り込む").first.click()

            print("7. 条件（1か月、土日祝）を選択します...")
            await page.locator("text=1ヶ月").first.click()
            await page.locator("text=土").first.click()
            await page.locator("text=日").nth(5).click()
            await page.locator("text=祝").first.click()

            print("8. 「表示」をクリックしてカレンダーを出します...")
            await page.locator("text=表示").nth(7).click()

            print("9. カレンダーの読み込みを待ちます...")
            await page.wait_for_timeout(3000)
            
            # =========================================================
            print("10. 画面のデータを取得して空きをチェックします...")
            
            html = await page.content() 
            soup = BeautifulSoup(html, 'html.parser')
            found_availabilities = []

            facility_rows = soup.find_all(lambda tag: tag.name == 'tr' and '庭球場' in tag.text)
            real_names = ["駒場庭球場", "区民センター庭球場", "碑文谷庭球場", "宮前公園庭球場"]
            
            for index, facility_row in enumerate(facility_rows):
                if index < len(real_names):
                    facility_name = real_names[index]
                else:
                    facility_name = f"予期せぬ庭球場（その{index + 1}）"
                
                marks = [cell.get_text(strip=True) for cell in facility_row.find_all(['td', 'th'])]
                    
                table = facility_row.find_parent('table')
                date_row = table.find('tr')
                dates = [cell.get_text(strip=True) for cell in date_row.find_all(['td', 'th'])]

                for i, mark in enumerate(marks):
                    if mark == "〇" or mark == "△":
                        try:
                            target_date = dates[i] 
                        except IndexError:
                            target_date = "日付不明"

                        msg = f"{facility_name} ＿ {target_date} ＿ 空きあり({mark})"
                        found_availabilities.append(msg)
                        print(f"🎉 発見: {msg}")

            # =========================================================
            SAVE_FILE = "previous_result.json"

            if os.path.exists(SAVE_FILE):
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    previous_availabilities = json.load(f)
            else:
                previous_availabilities = []

            if found_availabilities == previous_availabilities:
                print("前回と空き状況が全く同じなので、通知はスキップします。")
            else:
                print("🚨 前回から変化がありました！通知を送ります！")
                
                if len(found_availabilities) > 0:
                    try:
                        MY_EMAIL = os.environ.get("MY_EMAIL")
                        MY_PASSWORD = os.environ.get("MY_PASSWORD")
                        TO_EMAILS = ["soh050820@gmail.com","tangostin@gmail.com","emichiwawa0416@yahoo.co.jp"]
                        
                        subject = "🎾 テニスコート空き情報のお知らせ"
                        body = "以下のテニスコートに空きが出ました！\n\n" + "\n".join(found_availabilities)
                        
                        msg = MIMEText(body, "plain", "utf-8")
                        msg["Subject"] = subject
                        msg["From"] = MY_EMAIL
                        msg["To"] = ",".join(TO_EMAILS)
                        
                        server = smtplib.SMTP("smtp.gmail.com", 587)
                        server.starttls()
                        server.login(MY_EMAIL, MY_PASSWORD)
                        server.send_message(msg, to_addrs=TO_EMAILS)
                        server.quit()
                        print(f"✉️ ({len(TO_EMAILS)}名) へメールを送信しました！")
                        
                    except Exception as mail_err:
                        print(f"❌ メール送信エラー: {mail_err}")
                else:
                    print("空きがすべて埋まったため、メールはスキップします。")

                with open(SAVE_FILE, "w", encoding="utf-8") as f:
                    json.dump(found_availabilities, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"エラーが起きました: {e}")

        finally:
            await browser.close()
            print("テスト終了です！")

if __name__ == "__main__":
    asyncio.run(main())
