import csv, random
random.seed(42)

first = ["Aisha","Daniel","Fatima","Chidi","Grace","Samuel","Blessing","Ibrahim","Ngozi","Tunde",
"Mary","Kelechi","Zainab","Emeka","Hauwa","Victor","Amara","Bola","Sadiq","Joy","Peter","Halima",
"Stephen","Rita","Yakubu","Bukola","Musa","Chioma","Femi","Aminat","Gabriel","Esther","Nnamdi",
"Ruth","Sani","Patience","Uche","Maryam","Tobi","Funke","Idris","Ada","Segun","Hadiza","Obinna",
"Comfort","Yusuf","Ekene","Bisi","Abdul"]
last = ["Bello","Okafor","Yusuf","Eze","Adeyemi","Johnson","Nwosu","Sani","Obi","Bakare","Eteng",
"Amadi","Musa","Obiora","Lawal","Okeke","Akin","Effiong","Adamu","Idris","Udo","Anyanwu","Garba",
"Ogundipe","Balogun","Nwachukwu","Aliyu","Okonkwo","Adebayo","Mohammed","Ekwueme","Olawale"]
countries = ["UK","Canada","USA","Australia","Ireland","Germany"]
courses = ["MSc Data Science","MSc Computer Science","MBA","MSc Engineering","MS Finance",
"MSc Marketing","MSc Public Health","Foundation Business","MSc Pharmacy","MSc IT","MSc Nursing",
"MSc AI","Diploma","MSc Mechanical Eng","MSc Biotech","MSc Cybersecurity","MSc Management",
"MSc Economics","MSc HR","MS Data Analytics","MSc Logistics"]
classes = ["First","2:1","2:2","Third"]
fundings = ["Self-funded","Scholarship","Sponsor","Family","Bank loan","Education loan",
"Partial","Undecided","None"]
stages = ["Ready to apply","Application","Shortlisting","Evaluating","Comparing","Researching",
"Considering","New enquiry","Just enquired","Not sure","Cold","Unresponsive"]
sources = ["Meta Campaign","Google Ads","Webinar","Referral","Organic","TikTok Ads"]
engtests = ["ielts","toefl","duolingo","pte","none"]

rows=[]
for i in range(100):
    fn=random.choice(first); ln=random.choice(last)
    name=f"{fn} {ln}"
    email=f"{fn.lower()}.{ln.lower()}{i}@example.com"
    phone=f"+23480{random.randint(10000000,99999999)}"
    cls=random.choice(classes)
    gpa={"First":round(random.uniform(3.7,4.0),1),"2:1":round(random.uniform(3.3,3.7),1),
         "2:2":round(random.uniform(2.8,3.3),1),"Third":round(random.uniform(2.2,2.8),1)}[cls]
    et=random.choice(engtests)
    ielts=toefl=duo=pte=""
    if et=="ielts": ielts=round(random.uniform(5.5,8.5)*2)/2
    elif et=="toefl": toefl=random.randint(65,115)
    elif et=="duolingo": duo=random.randint(85,145)
    elif et=="pte": pte=random.randint(50,85)
    funding=random.choice(fundings)
    budget=random.choice([4000,8000,11000,15000,18000,22000,26000,30000,35000,42000,48000])
    intake=random.choice(["2026/2027","2026/2027","2026/2027","2027/2028",
                          "2027/2028","2028/2029","2029/2030"])
    country=random.choice(countries)
    course=random.choice(courses)
    stage=random.choice(stages)
    source=random.choice(sources)
    rows.append([name,email,phone,gpa,cls,ielts,toefl,pte,duo,funding,budget,intake,country,course,stage,source])

with open("sample_data.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    w.writerow(["name","email","phone","gpa","grade_class","ielts","toefl","pte","duolingo",
"funding_type","budget","intake_year","target_country","target_course","stage","source"])
    w.writerows(rows)
print("wrote",len(rows),"rows")
