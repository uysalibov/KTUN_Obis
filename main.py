from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import cv2
import os
import json
import numpy as np
import time
import requests

import settings # settings.py dosyasına girip gerekli bilgileri doldurun

# Tarayıcı ayarları
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--headless') # tarayıcının açılmasını istiyorsan bu satırı yorum satırı yap

# Tarayıcı
browser = webdriver.Chrome('chromedriver', chrome_options=chrome_options)
while True:
    flag = 0
    while(flag == 0):
        # Okul sayfasına git
        browser.get("https://obis.ktun.edu.tr")

        # Captcha elementini bul ve resmini çek
        element = browser.find_element_by_id('Image1')
        screenshot_as_bytes = element.screenshot_as_png
        with open('captcha.png', 'wb') as f:
            f.write(screenshot_as_bytes)



        numbers = []
        img_rgb = cv2.imread('captcha.png')

        # Her harf için tarama yap
        for digit in os.listdir('./digits'):
            template = cv2.imread(f'./digits/{digit}')
            w, h = template.shape[:-1] # resim boyutları

            # sayının resim içinde olup olmadığını bulma
            res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED) 
            threshold = .8 # eşik değeri
            loc = np.where(res >= threshold)
            for pt in zip(*loc[::-1]):
                
                # bulunan her resmin üzerini çizip tekrar bulunmasını engelliyoruz
                cv2.line(img_rgb, (pt[0] + int(w/2), pt[1]), (pt[0] + int(w/2), pt[1] + int(h/2)), (0, 0, 255), 1)
                rounded = round(pt[0]/10)*10

                # bulunanların listeye eklenmesi
                numbers.append(
                    {
                        'Loc': int(rounded),
                        'Number': int(digit[0])
                    }
                )
            
            # tekrar eden değerleri listeden silme
            of = []
            for si in numbers:
                key = si["Loc"]
                if key not in of:
                    of.append(key)
                else:
                    numbers.remove(si)
                

        # resmin son halinin kaydedilmesi
        cv2.imwrite('result.png', img_rgb)

        # bulunan sayıları soldan sağa doğru sıralama
        newNumbers = sorted(numbers, key=lambda k: k['Loc'])
        print(newNumbers)
        captcha = ''
        for i in newNumbers:
            captcha += str(i['Number'])

        print(captcha)

        browser.find_element_by_xpath('//input[@name="id"]').send_keys(settings.EMAIL) # mail adresini gir
        browser.find_element_by_xpath('//input[@name="pass"]').send_keys(settings.PASSWORD) # şifreyi gir
        browser.find_element_by_xpath('//input[@name="TxtCaptcha"]').send_keys(captcha) # captcha kodunu gir

        browser.find_element_by_xpath('//button[@type="submit"]').click() # gönder

        # eğer bizi yönlendirdiyse döngü bitsin
        print(browser.current_url)
        if browser.current_url == 'https://obis.ktun.edu.tr/Ogrenci/Anasayfa':
            flag = 1
        time.sleep(0.5)

    # Not sayfasına git
    browser.get('https://obis.ktun.edu.tr/Ogrenci/NotDurumu')


    # tüm ders satırlarını bul
    lessons = browser.find_elements_by_xpath('(//table[@id="dynamic-table"])[2]/tbody/tr')

    # tüm hepsini teker teker listeye sözlük olarak al
    notlarJson = []
    try:
        for lesson in lessons:
            lessonInfo = lesson.find_elements_by_xpath('.//td[@class="text-center"]')
            
            notlarJson.append({
                'Ders Kodu': lessonInfo[0].text,
                'Yıl': lessonInfo[1].text,
                'Ders Adı': lessonInfo[2].text,
                'Kredi': lessonInfo[3].text,
                'Katsayı': lessonInfo[4].text,
                'Muaf': lessonInfo[5].text,
                'Ara Sınav1': lessonInfo[6].text,
                'Ara Sınav2': lessonInfo[7].text,
                'Genel Sınav': lessonInfo[8].text,
                'Bütünleme': lessonInfo[9].text,
                'Tek Ders': lessonInfo[10].text,
                'Harf': lessonInfo[11].text
            })

    except IndexError: # bazen en sonda boş liste dahil olabiliyor
        pass

    # eğer notlar.json dosyası yoksa oluşturuyor
    if not os.path.exists("notlar.json"):
        notlar = open("notlar.json", "w+", encoding='utf-8')
        json.dump(notlarJson, notlar, indent=4, ensure_ascii=False)
    else: # dosyadaki bilgilerle yeni alınan bilgiler uyuşmuyorsa değiştiriyor
        notlar = open("notlar.json", "r", encoding='utf-8')
        json_file = json.loads(notlar.read())
        degisenNotlar = []
        flagLesson = 0
        for (item, i) in zip(notlarJson, json_file):
            if i != item:
                degisenNotlar.append(item)
                flagLesson += 1

        notlar.close()

        # değişiklik olursa bunları discord webhook'a gönderiyor
        if flagLesson != 0:
            notlar = open("notlar.json", "w", encoding='utf-8')
            json.dump(notlarJson, notlar, indent=4, ensure_ascii=False)
            print(degisenNotlar)
            for i in degisenNotlar:
                message = f"**Not Güncellemesi** - <@{settings.DISCORD_USER_ID}>\n"
                for index in list(i.items()):
                    message += f"*{index[0]}* : {index[1]}\n"
                
                requests.post(settings.WEBHOOK_URL, data={'content':message})
        else:
            print('Değişiklik yok')
            
        
    # 15 dakika bekleme ve ardından yeniden başlama
    browser.close()
    print('15 dakika bekleniyor')
    time.sleep(900)