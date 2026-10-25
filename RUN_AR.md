# دليل تشغيل Nimbus خطوة بخطوة

هذا الدليل يشرح تشغيل المشروع بطريقتين:

1. تشغيل تجريبي على جهاز Windows.
2. نشر نسخة مجانية على الإنترنت باستخدام Netlify للواجهة وPythonAnywhere للخادم.

المشروع موجود في مستودع GitHub العام:
https://github.com/xfoors16-tech/nimbus-private-cloud

## أولًا: تشغيله على جهازك (Windows)

### المتطلبات

- Python 3.12 أو أحدث.
- Node.js وnpm.
- اتصال إنترنت عند تثبيت الحزم لأول مرة.

لا تحتاج Docker للتشغيل المحلي.

### تشغيل الـAPI

افتح PowerShell في مجلد المشروع، ثم نفّذ:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Set-Location backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8001
```

اترك نافذة PowerShell هذه مفتوحة. إذا منع PowerShell تفعيل البيئة، افتح Command Prompt بدلًا منه، أو نفّذ أوامر Python من غير تفعيل البيئة باستخدام:

```powershell
python -m pip install -r backend\requirements.txt
```

### تشغيل الواجهة

افتح نافذة PowerShell ثانية في مجلد المشروع:

```powershell
Set-Location "C:\Users\hp pc\OneDrive\Desktop\Private Cloud Storage Platform\frontend"
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

اترك النافذتين مفتوحتين، ثم افتح:

- التطبيق: http://localhost:5173
- توثيق الـAPI: http://localhost:8001/docs
- فحص جاهزية الـAPI: http://localhost:8001/api/v1/health

سجّل حسابًا جديدًا من صفحة الدخول. قاعدة بيانات SQLite والملفات التي ترفعها تحفظ محليًا تحت `backend\data`.

### إيقاف التشغيل المحلي

في كل نافذة شغّالة، اضغط `Ctrl+C`.

### بيانات التشغيل والنسخ الاحتياطي المحلي

- قاعدة البيانات: `backend\data\private-cloud.db`
- الملفات: `backend\data\objects`

للاحتفاظ بملفاتك، انسخ قاعدة البيانات ومجلد الملفات إلى مكان آمن بعد إيقاف الـAPI. لا تحذف `backend\data` إذا كانت تحتوي بيانات تريد الاحتفاظ بها.

## ثانيًا: نشر نسخة مجانية على الإنترنت

### ملاحظة مهمة قبل النشر

الموقع العام لا يعمل بالكامل بمجرد نشر الواجهة؛ يحتاج خادم API شغالًا أيضًا. الرابط المنشور حاليًا كان موجّهًا إلى خدمة Render غير موجودة، وهذا سبب ظهور `Request failed (404)`. الحل المجاني أدناه يشغّل الـAPI في PythonAnywhere بدل Render.

خطة PythonAnywhere المجانية مناسبة **للتجربة فقط** وليست تخزينًا سحابيًا موثوقًا للملفات المهمة. المساحة الإجمالية للحساب محدودة ومشتركة بين البرنامج وقاعدة البيانات وكل الملفات، وقد تتغير قيود الخطة بمرور الوقت. إعداد العرض يحدد:

- الحد الأقصى للملف الواحد: 5 MiB.
- الحصة الافتراضية لكل حساب: 50 MiB.
- قاعدة البيانات والملفات على قرص PythonAnywhere المحلي؛ لا يوجد S3 أو نسخ احتياطي تلقائي.
- لا ترفع ملفات حساسة أو مهمة، ولا تعتمد على الخدمة لحفظ نسخة وحيدة من ملفاتك.

### الخطوة 1: إنشاء حساب PythonAnywhere مجاني

1. افتح https://www.pythonanywhere.com/registration/register/beginner/
2. أنشئ حساب **Beginner / Free** وسجّل اسم المستخدم الذي اخترته.
3. لا ترسل كلمة المرور أو أي بيانات دخول لأحد.

سيكون عنوان الـAPI على الشكل:

```text
https://YOUR_USERNAME.pythonanywhere.com
```

استبدل `YOUR_USERNAME` باسم حسابك في كل الخطوات التالية.

### الخطوة 2: تنزيل البرنامج وتثبيت حزم Python

من لوحة PythonAnywhere افتح **Consoles** ثم **Bash**. نفّذ:

```bash
git clone https://github.com/xfoors16-tech/nimbus-private-cloud.git
cd ~/nimbus-private-cloud/backend
```

اختر إصدار Python متوفرًا في حسابك، ويفضل 3.12 أو أحدث. افحص الإصدارات المتوفرة:

```bash
ls /usr/bin/python3.*
```

أنشئ البيئة الافتراضية باستخدام إصدار موجود بالفعل. المثال التالي يفترض أن Python 3.12 موجود:

```bash
mkvirtualenv --python=/usr/bin/python3.12 nimbus
pip install -r requirements-pythonanywhere.txt
```

إذا كان المتوفر إصدارًا آخر، بدّل `python3.12` في الأمر إلى اسم الإصدار الموجود. أنشئ مكان قاعدة البيانات والملفات ثم طبّق ترحيلات قاعدة البيانات:

```bash
mkdir -p ~/nimbus-data/objects
export DATABASE_URL="sqlite:////home/$USER/nimbus-data/private-cloud.db"
export STORAGE_BACKEND=local
export STORAGE_ROOT="/home/$USER/nimbus-data/objects"
python -m alembic upgrade head
```

يجب أن ينتهي الأمر الأخير بنجاح. لا ترفع مجلد `nimbus-data` إلى GitHub.

### الخطوة 3: إنشاء Web app على PythonAnywhere

1. افتح تبويب **Web**.
2. اضغط **Add a new web app**.
3. اختر النطاق المجاني الذي ينتهي بـ `pythonanywhere.com`.
4. اختر **Manual configuration**، ثم اختر إصدار Python نفسه الذي استخدمته للبيئة الافتراضية.
5. في خانة **Virtualenv** أدخل المسار، مع استبدال اسم المستخدم:

   ```text
   /home/YOUR_USERNAME/.virtualenvs/nimbus
   ```

### الخطوة 4: إعداد WSGI

من تبويب **Web** افتح رابط ملف WSGI الظاهر هناك. امسح محتوى الملف المولّد واستبدله بالنص التالي بعد تبديل `YOUR_USERNAME` باسم حسابك و`YOUR_SITE.netlify.app` برابط موقع Netlify:

```python
import os
import sys

username = "YOUR_USERNAME"
project_path = f"/home/{username}/nimbus-private-cloud/backend"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ["DATABASE_URL"] = (
    f"sqlite:////home/{username}/nimbus-data/private-cloud.db"
)
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_ROOT"] = f"/home/{username}/nimbus-data/objects"
os.environ["SESSION_COOKIE_SECURE"] = "true"
os.environ["SESSION_COOKIE_SAMESITE"] = "lax"
os.environ["DEFAULT_QUOTA_BYTES"] = str(50 * 1024 * 1024)
os.environ["MAX_UPLOAD_BYTES"] = str(5 * 1024 * 1024)
os.environ["CORS_ORIGINS"] = "https://YOUR_SITE.netlify.app"

from pythonanywhere_wsgi import application
```

احفظ ملف WSGI، ثم ارجع إلى تبويب **Web** واضغط **Reload**.

### الخطوة 5: اختبار الـAPI على الإنترنت

افتح الرابط التالي في المتصفح بعد استبدال اسم المستخدم:

```text
https://YOUR_USERNAME.pythonanywhere.com/api/v1/health
```

النتيجة السليمة:

```json
{"status":"ok"}
```

إذا ظهر خطأ، راجع رابط **Error log** في تبويب **Web** على PythonAnywhere. أكثر الأسباب شيوعًا:

- `ModuleNotFoundError`: مسار البيئة الافتراضية أو مجلد المشروع في WSGI غير صحيح.
- خطأ في قاعدة البيانات: تأكد أن أوامر الترحيل انتهت بنجاح وأن مسار `nimbus-data` يطابق المسار في WSGI.
- `404`: تأكد من المسار `/api/v1/health`، ثم اضغط Reload للتطبيق.

### الخطوة 6: توصيل Netlify بخادم PythonAnywhere

ملف `netlify.toml` في GitHub يوجّه `/api/*` إلى عنوان Render القديم؛ يجب تغييره إلى عنوان PythonAnywhere حتى يعمل التسجيل.

1. افتح ملف [`netlify.toml`](https://github.com/xfoors16-tech/nimbus-private-cloud/blob/main/netlify.toml) في GitHub.
2. اضغط رمز القلم **Edit**.
3. ابحث عن هذا السطر:

   ```toml
   to = "https://nimbus-private-cloud-api-xfoors16.onrender.com/api/:splat"
   ```

4. غيّره إلى رابط حسابك، مثل:

   ```toml
   to = "https://YOUR_USERNAME.pythonanywhere.com/api/:splat"
   ```

5. استبدل `YOUR_USERNAME` باسمك الحقيقي، ثم اضغط **Commit changes** على فرع `main`.
6. في Netlify، انتظر اكتمال النشر التلقائي. إذا لم يبدأ تلقائيًا، اختر **Deploys → Trigger deploy**.

افتح رابط Netlify بعد نجاح النشر، وأنشئ حسابًا تجريبيًا، ثم اختبر تسجيل الخروج والدخول ورفع صورة شخصية ورفع ملف صغير وتنزيله.

## حل الأخطاء الشائعة

### `Request failed (404)`

عنوان API في توجيه Netlify غير صحيح، أو خدمة PythonAnywhere لم تُنشأ/تُعدّ بعد. افتح أولًا:

```text
https://YOUR_USERNAME.pythonanywhere.com/api/v1/health
```

إذا لم ترَ `{"status":"ok"}`، أصلح خادم PythonAnywhere. إذا كان الفحص سليمًا، راجع عنوان `to` في `netlify.toml` على GitHub وانتظر إعادة نشر Netlify.

### `502 Bad Gateway`

خادم PythonAnywhere متوقف أو لم يُعمل له Reload، أو عنوانه في `netlify.toml` خطأ. اختبر `/api/v1/health` مباشرة، ثم افحص Error log واضغط Reload.

### الحساب يسجّل، لكن الصور أو الملفات لا تظهر بعد إعادة النشر

خطة العرض تحفظها على مساحة الحساب المحلية. تحقق أن `DATABASE_URL` و`STORAGE_ROOT` في WSGI يشيران إلى `/home/YOUR_USERNAME/nimbus-data`، وليس داخل مجلد المشروع. لا تحذف مجلد البيانات.

### الملف كبير أو الرفع بطيء

حد الملف في إعداد العرض 5 MiB. Netlify يمرر الطلبات عبر proxy له حد زمني؛ ابدأ بتجربة ملف صغير. لا ترفع ملفات كبيرة أو مهمة إلى الخطة المجانية.

## تشغيل الاختبارات

من جذر المشروع في PowerShell:

```powershell
Set-Location backend
python -m pytest tests -q
Set-Location ..\frontend
npm.cmd ci
npm.cmd test
npm.cmd run build
```

## ملاحظات أمان

- لا تضف كلمات مرور أو مفاتيح S3 أو ملفات `.env` إلى GitHub.
- إعداد PythonAnywhere المجاني لا يستخدم S3؛ تخزينه محلي ومحدود.
- لا تشارك ملف قاعدة البيانات أو مجلد ملفات المستخدمين.
- هذه نسخة عرض وتجربة، وليست خدمة مضمونة لحفظ الملفات على المدى الطويل.
