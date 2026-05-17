import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime
import re

def normalize(text):
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'[ةه]', 'ه', text)
    text = re.sub(r'[\u064B-\u065F]', '', text)
    text = re.sub(r'^ال|(?<=\s)ال', '', text)
    text = text.strip()
    return text
# ══════════════════════════════════════════════
#           إعدادات البوت الأساسية
# ══════════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ══════════════════════════════════════════════
#           متغيرات الفعالية
# ══════════════════════════════════════════════
questions = []          # قائمة الأسئلة (صورة + جواب)
scores = {}             # نقاط اللاعبين {user_id: points}
event_active = False    # هل الفعالية شغّالة؟
current_question = -1   # رقم السؤال الحالي
answered = False        # هل تم الإجابة على السؤال الحالي؟
event_channel = None    # القناة التي تجري فيها الفعالية
waiting_for_answer = False  # هل ننتظر إجابة الآن؟
ALLOWED_ROLES = [1497836398676545546, 1497836322310721678, 1497836395711037512, 1498132684432474304, 1502687285446180964]
DATA_FILE = "questions.json"  # ملف حفظ الأسئلة

# ══════════════════════════════════════════════
#           تحميل وحفظ الأسئلة
# ══════════════════════════════════════════════
def load_questions():
    global questions
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            questions = json.load(f)
    else:
        questions = []

def save_questions():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

# ══════════════════════════════════════════════
#           عند تشغيل البوت
# ══════════════════════════════════════════════
@bot.event
async def on_ready():
    load_questions()
    print(f"✅ البوت شغّال: {bot.user.name}")
    print(f"📦 عدد الأسئلة المحفوظة: {len(questions)}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="🖼️ فعاليات الصور | !مساعدة"
        )
    )

# ══════════════════════════════════════════════
#           إضافة سؤال جديد (صورة + جواب)
# ══════════════════════════════════════════════
@bot.command(name="اضف")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def add_question(ctx, *, answer: str = None):
    """
    طريقة الاستخدام:
    ارفع صورة وفي خانة الوصف اكتب: !اضف الجواب
    """
    if not ctx.message.attachments:
        embed = discord.Embed(
            title="❌ خطأ",
            description="يجب أن ترفق صورة مع الأمر!\n\n**الطريقة الصحيحة:**\nارفع صورة واكتب في وصفها:\n`!اضف الجواب`",
            color=0xFF4444
        )
        await ctx.send(embed=embed)
        return

    if not answer:
        embed = discord.Embed(
            title="❌ خطأ",
            description="يجب أن تكتب الجواب بعد الأمر!\n\n**مثال:** `!اضف برج إيفل`",
            color=0xFF4444
        )
        await ctx.send(embed=embed)
        return

    image_url = ctx.message.attachments[0].url
    question_number = len(questions) + 1

    questions.append({
        "number": question_number,
        "image_url": image_url,
        "answer": answer.strip().lower(),
        "answer_display": answer.strip()
    })

    save_questions()

    embed = discord.Embed(
        title="✅ تم إضافة السؤال بنجاح!",
        color=0x00CC66
    )
    embed.add_field(name="📌 رقم السؤال", value=f"`{question_number}`", inline=True)
    embed.add_field(name="✏️ الجواب", value=f"`{answer.strip()}`", inline=True)
    embed.add_field(name="📦 إجمالي الأسئلة", value=f"`{len(questions)}`", inline=True)
    embed.set_thumbnail(url=image_url)
    embed.set_footer(text="فعاليات الصور 🖼️")
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════
#           عرض قائمة الأسئلة
# ══════════════════════════════════════════════
@bot.command(name="الاسئلة")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def list_questions(ctx):
    if not questions:
        embed = discord.Embed(
            title="📭 لا توجد أسئلة",
            description="لم يتم إضافة أي أسئلة بعد.\nاستخدم `!اضف` لإضافة أسئلة.",
            color=0xFFAA00
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="📋 قائمة الأسئلة المضافة",
        description=f"إجمالي الأسئلة: **{len(questions)}**",
        color=0x5865F2
    )

    for i, q in enumerate(questions):
        embed.add_field(
            name=f"سؤال {q['number']}",
            value=f"الجواب: `{q['answer_display']}`",
            inline=True
        )

    embed.set_footer(text="فعاليات الصور 🖼️ | استخدم !مسح لحذف جميع الأسئلة")
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════
#           حذف سؤال معين
# ══════════════════════════════════════════════
@bot.command(name="احذف")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def delete_question(ctx, number: int):
    global questions

    q = next((q for q in questions if q["number"] == number), None)
    if not q:
        embed = discord.Embed(
            title="❌ لم يُعثر على السؤال",
            description=f"لا يوجد سؤال برقم `{number}`",
            color=0xFF4444
        )
        await ctx.send(embed=embed)
        return

    questions = [x for x in questions if x["number"] != number]
    # إعادة ترقيم الأسئلة
    for i, q in enumerate(questions):
        q["number"] = i + 1
    save_questions()

    embed = discord.Embed(
        title="🗑️ تم الحذف",
        description=f"تم حذف السؤال رقم `{number}` بنجاح.",
        color=0x00CC66
    )
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════
#           مسح جميع الأسئلة
# ══════════════════════════════════════════════
@bot.command(name="مسح")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def clear_questions(ctx):
    global questions

    if not questions:
        await ctx.send("📭 لا توجد أسئلة أصلاً!")
        return

    # رسالة تأكيد
    embed = discord.Embed(
        title="⚠️ تأكيد الحذف",
        description=f"هل أنت متأكد أنك تريد حذف **{len(questions)} سؤال**؟\nاكتب `نعم` للتأكيد أو `لا` للإلغاء.",
        color=0xFFAA00
    )
    await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content in ["نعم", "لا"]

    try:
        msg = await bot.wait_for("message", timeout=15.0, check=check)
        if msg.content == "نعم":
            questions = []
            save_questions()
            await ctx.send("✅ تم مسح جميع الأسئلة بنجاح!")
        else:
            await ctx.send("❌ تم إلغاء العملية.")
    except asyncio.TimeoutError:
        await ctx.send("⏰ انتهى الوقت، تم إلغاء العملية.")

# ══════════════════════════════════════════════
#           بدء الفعالية
# ══════════════════════════════════════════════
@bot.command(name="ابدأ")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def start_event(ctx):
    global event_active, current_question, scores, event_channel, answered, waiting_for_answer

    if event_active:
        await ctx.send("⚠️ هناك فعالية تجري الآن بالفعل!")
        return

    if len(questions) == 0:
        embed = discord.Embed(
            title="❌ لا توجد أسئلة!",
            description="يجب أن تضيف أسئلة أولاً باستخدام أمر `!اضف`",
            color=0xFF4444
        )
        await ctx.send(embed=embed)
        return

    # إعداد الفعالية
    event_active = True
    current_question = 0
    scores = {}
    event_channel = ctx.channel
    answered = False
    waiting_for_answer = False

    # رسالة البداية
    embed = discord.Embed(
        title="🎉 انطلاق فعالية الصور! 🎉",
        description=(
            f"**عدد الأسئلة:** {len(questions)} سؤال 🖼️\n\n"
            "📌 **كيف تلعب؟**\n"
            "• سيرسل البوت صورة\n"
            "• اكتب الجواب في الشات مباشرة\n"
            "• أول من يجيب صح يأخذ النقطة ✅\n\n"
            "⏱️ **الفعالية تبدأ بعد 5 ثواني...**"
        ),
        color=0xFFD700
    )
    embed.set_footer(text="فعاليات الصور 🖼️ | بالتوفيق للجميع!")
    await ctx.send(embed=embed)

    await asyncio.sleep(5)
    await send_question(ctx.channel)

# ══════════════════════════════════════════════
#           إرسال السؤال
# ══════════════════════════════════════════════
async def send_question(channel):
    global answered, waiting_for_answer

    answered = False
    waiting_for_answer = True
    q = questions[current_question]

    embed = discord.Embed(
        title=f"🖼️ السؤال {current_question + 1} من {len(questions)}",
        description="**ما هو الجواب؟ اكتبه الآن! ⬇️**",
        color=0x5865F2
    )
    embed.set_image(url=q["image_url"])
    embed.set_footer(text="فعاليات الصور 🖼️ | أسرع من يجيب يأخذ النقطة!")
    await channel.send(embed=embed)

# ══════════════════════════════════════════════
#           مراقبة الإجابات
# ══════════════════════════════════════════════
@bot.event
async def on_message(message):
    global answered, current_question, event_active, waiting_for_answer

    # تجاهل رسائل البوت
    if message.author.bot:
        await bot.process_commands(message)
        return

    # معالجة الأوامر أولاً
    await bot.process_commands(message)

    # إذا الفعالية شغّالة وننتظر إجابة
    if event_active and waiting_for_answer and not answered:
        if message.channel == event_channel:
            q = questions[current_question]
            user_answer = message.content.strip().lower()
            user_answer = normalize(user_answer)


            # التحقق من الإجابة (يحتوي على الكلمة الصحيحة)
            if normalize(q["answer"]) in normalize(user_answer):
                answered = True
                waiting_for_answer = False

                # إضافة نقطة
                user_id = message.author.id
                user_name = message.author.display_name
                if user_id not in scores:
                    scores[user_id] = {"name": user_name, "points": 0}
                scores[user_id]["points"] += 1
                scores[user_id]["name"] = user_name  # تحديث الاسم

                # رسالة الفوز
                embed = discord.Embed(
                    title="🎯 إجابة صحيحة!",
                    description=(
                        f"🏆 **{user_name}** أجاب صح!\n"
                        f"✅ الجواب: **{q['answer_display']}**\n"
                        f"⭐ نقاطه الآن: **{scores[user_id]['points']}**"
                    ),
                    color=0x00FF88
                )

                # هل هناك سؤال تالي؟
                if current_question + 1 < len(questions):
                    embed.add_field(
                        name="⏳ التالي",
                        value=f"السؤال القادم بعد **10 ثواني**...",
                        inline=False
                    )

                await message.channel.send(embed=embed)

                # الانتقال للسؤال التالي
                if current_question + 1 < len(questions):
                    await asyncio.sleep(10)
                    current_question += 1
                    await send_question(event_channel)
                else:
                    await end_event(event_channel)

# ══════════════════════════════════════════════
#           إنهاء الفعالية وعرض النتائج
# ══════════════════════════════════════════════
async def end_event(channel):
    global event_active, waiting_for_answer

    event_active = False
    waiting_for_answer = False

    # ترتيب اللاعبين
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["points"], reverse=True)

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    embed = discord.Embed(
        title="🏁 انتهت الفعالية! 🏁",
        description="**🏆 المراكز الخمسة الأولى 🏆**",
        color=0xFFD700,
        timestamp=datetime.utcnow()
    )

    if not sorted_scores:
        embed.add_field(
            name="😔 لا يوجد فائزون",
            value="لم يجب أحد على أي سؤال!",
            inline=False
        )
    else:
        top5 = sorted_scores[:5]
        leaderboard_text = ""
        for i, (uid, data) in enumerate(top5):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            leaderboard_text += f"{medal} **{data['name']}** — {data['points']} نقطة\n"

        embed.add_field(name="النتائج", value=leaderboard_text, inline=False)

    embed.add_field(
        name="📊 إحصائيات",
        value=f"عدد الأسئلة: **{len(questions)}** | عدد المشاركين: **{len(scores)}**",
        inline=False
    )
    embed.set_footer(text="فعاليات الصور 🖼️ | شكراً لجميع المشاركين!")

    await channel.send(embed=embed)

# ══════════════════════════════════════════════
#           إيقاف الفعالية يدوياً
# ══════════════════════════════════════════════
@bot.command(name="ايقاف")
@commands.has_permissions(administrator=True)
@commands.has_any_role(*ALLOWED_ROLES)
async def stop_event(ctx):
    global event_active, waiting_for_answer

    if not event_active:
        await ctx.send("⚠️ لا توجد فعالية تجري الآن!")
        return

    event_active = False
    waiting_for_answer = False

    embed = discord.Embed(
        title="⛔ تم إيقاف الفعالية",
        description=f"أوقف الفعالية **{ctx.author.display_name}**\nتم إيقاف الفعالية عند السؤال رقم {current_question + 1}",
        color=0xFF4444
    )
    await ctx.send(embed=embed)
    await end_event(ctx.channel)

# ══════════════════════════════════════════════
#           النقاط الحالية أثناء الفعالية
# ══════════════════════════════════════════════
@bot.command(name="النقاط")
async def show_scores(ctx):
    if not scores:
        await ctx.send("📭 لا توجد نقاط بعد!")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["points"], reverse=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

    embed = discord.Embed(
        title="📊 النقاط الحالية",
        color=0x5865F2
    )

    text = ""
    for i, (uid, data) in enumerate(sorted_scores[:5]):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} **{data['name']}** — {data['points']} نقطة\n"

    embed.add_field(name="المتصدرون", value=text or "لا يوجد", inline=False)
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════
#           أمر المساعدة
# ══════════════════════════════════════════════
@bot.command(name="مساعدة")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 أوامر بوت فعاليات الصور",
        description="بوت الألعاب العربي 🖼️",
        color=0x5865F2
    )

    embed.add_field(
        name="🔧 أوامر المشرف",
        value=(
            "`!اضف [جواب]` — أضف صورة مع جوابها (ارفق صورة)\n"
            "`!الاسئلة` — عرض جميع الأسئلة المضافة\n"
            "`!احذف [رقم]` — حذف سؤال معين\n"
            "`!مسح` — حذف جميع الأسئلة\n"
            "`!ابدأ` — بدء الفعالية\n"
            "`!ايقاف` — إيقاف الفعالية"
        ),
        inline=False
    )

    embed.add_field(
        name="👥 أوامر اللاعبين",
        value=(
            "`!النقاط` — عرض النقاط الحالية\n"
            "`!مساعدة` — عرض هذه القائمة"
        ),
        inline=False
    )

    embed.add_field(
        name="🎮 كيف تلعب؟",
        value=(
            "• ينتظر البوت رسالتك في الشات\n"
            "• اكتب الجواب مباشرة — لا حاجة لأمر\n"
            "• إذا كانت رسالتك تحتوي على الجواب = نقطة ✅"
        ),
        inline=False
    )

    embed.set_footer(text="فعاليات الصور 🖼️ | بالتوفيق!")
    await ctx.send(embed=embed)

# ══════════════════════════════════════════════
#           معالجة الأخطاء
# ══════════════════════════════════════════════
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ هذا الأمر للمشرفين فقط!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ ناقص معلومة! استخدم `!مساعدة` لرؤية الطريقة الصحيحة.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # تجاهل الأوامر غير الموجودة

# ══════════════════════════════════════════════
#           تشغيل البوت
# ══════════════════════════════════════════════
TOKEN = os.environ.get("DISCORD_TOKEN", "ضع_التوكن_هنا")

if TOKEN == "ضع_التوكن_هنا":
    print("❌ خطأ: لم يتم وضع التوكن!")
    print("📌 ضع توكن البوت في متغير البيئة DISCORD_TOKEN")
else:
    bot.run(TOKEN)
