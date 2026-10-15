def check_score(score):
    if score >=60:
        return  "及格"
    else:
        return  "不及格"

def get_grade(score):
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"

def calc_bmi(height, weight):
    bmi = weight / (height * height)
    if bmi < 18.5:
        result = '过轻'
    elif 18.5 <= bmi <= 25:
        result = '正常'
    elif 25 <= bmi <= 28:
        result = '过重'
    elif bmi < 32:
        result = '肥胖'
    else:
        result = '严重肥胖'
    return f'BMI为{bmi},体型属于{result}'



if __name__ == '__main__':
    print(check_score(70))
    print(get_grade(80))
    print(calc_bmi(1.65, 60))