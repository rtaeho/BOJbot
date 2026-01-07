import os
import json
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 설정
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"


def load_users() -> list:
    """저장된 유저 데이터 불러오기"""
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_users(users: list):
    """유저 데이터 저장"""
    DATA_DIR.mkdir(exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_solved_count(boj_id: str) -> dict | None:
    """solved.ac API로 유저 정보 가져오기"""
    url = f"https://solved.ac/api/v3/user/show?handle={boj_id}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "solvedCount": data.get("solvedCount", 0),
                "tier": data.get("tier", 0),
            }
        elif response.status_code == 404:
            return None
    except Exception as e:
        print(f"API 에러: {e}")
        return None
    return None


def get_tier_name(tier: int) -> str:
    """티어 숫자를 이름으로 변환"""
    tiers = ["Unrated", "Bronze V", "Bronze IV", "Bronze III", "Bronze II", "Bronze I",
             "Silver V", "Silver IV", "Silver III", "Silver II", "Silver I",
             "Gold V", "Gold IV", "Gold III", "Gold II", "Gold I",
             "Platinum V", "Platinum IV", "Platinum III", "Platinum II", "Platinum I",
             "Diamond V", "Diamond IV", "Diamond III", "Diamond II", "Diamond I",
             "Ruby V", "Ruby IV", "Ruby III", "Ruby II", "Ruby I", "Master"]
    return tiers[tier] if 0 <= tier < len(tiers) else "Unknown"


def send_discord_message(content: str):
    """디스코드 웹훅으로 메시지 전송"""
    if not WEBHOOK_URL:
        print("WEBHOOK_URL이 설정되지 않았습니다.")
        return False

    try:
        response = requests.post(
            WEBHOOK_URL,
            json={"content": content},
            timeout=10
        )
        return response.status_code == 204
    except Exception as e:
        print(f"웹훅 전송 에러: {e}")
        return False


def check_all_users():
    """모든 유저의 인증 현황 체크"""
    users = load_users()
    if not users:
        print("등록된 유저가 없습니다.")
        return

    results = []
    success_count = 0
    today = datetime.now().strftime("%Y-%m-%d")

    for user in users:
        boj_id = user["boj_id"]
        name = user["name"]
        last_count = user.get("solved_count", 0)

        data = get_solved_count(boj_id)
        if data is None:
            results.append(f"⚠️ **{name}** ({boj_id}): 조회 실패")
            continue

        current_count = data["solvedCount"]
        diff = current_count - last_count

        if diff > 0:
            results.append(f"✅ **{name}** ({boj_id}): +{diff}문제")
            success_count += 1
        else:
            results.append(f"❌ **{name}** ({boj_id}): 0문제")

        # 카운트 업데이트
        user["solved_count"] = current_count
        user["last_checked"] = datetime.now().isoformat()

    save_users(users)

    total = len(users)
    message = (
        f"📊 **{today} 일일 인증 현황**\n\n"
        + "\n".join(results)
        + f"\n\n🎯 **{success_count}/{total}명** 인증 완료!"
    )

    print(message)
    print()

    if send_discord_message(message):
        print("디스코드 전송 완료!")
    else:
        print("디스코드 전송 실패")


def reset_counts():
    """현재 기준으로 카운트 리셋 (새로 시작할 때 사용)"""
    users = load_users()

    for user in users:
        data = get_solved_count(user["boj_id"])
        if data:
            user["solved_count"] = data["solvedCount"]
            user["last_checked"] = datetime.now().isoformat()
            print(f"{user['name']} ({user['boj_id']}): {data['solvedCount']}문제로 리셋")

    save_users(users)
    print("\n리셋 완료!")


def add_user(boj_id: str, name: str):
    """새 유저 추가"""
    data = get_solved_count(boj_id)
    if data is None:
        print(f"'{boj_id}'를 찾을 수 없습니다.")
        return

    users = load_users()

    # 중복 체크
    for user in users:
        if user["boj_id"] == boj_id:
            print(f"'{boj_id}'는 이미 등록되어 있습니다.")
            return

    users.append({
        "boj_id": boj_id,
        "name": name,
        "solved_count": data["solvedCount"],
        "registered_at": datetime.now().isoformat(),
        "last_checked": datetime.now().isoformat(),
    })
    save_users(users)

    tier_name = get_tier_name(data["tier"])
    print(f"등록 완료!")
    print(f"- 이름: {name}")
    print(f"- 백준 ID: {boj_id}")
    print(f"- 티어: {tier_name}")
    print(f"- 현재 푼 문제: {data['solvedCount']}문제")


def list_users():
    """등록된 유저 목록 출력"""
    users = load_users()
    if not users:
        print("등록된 유저가 없습니다.")
        return

    print("📋 등록된 유저 목록:\n")
    for user in users:
        print(f"- {user['name']} ({user['boj_id']}): {user.get('solved_count', 0)}문제")


def remove_user(boj_id: str):
    """유저 삭제"""
    users = load_users()
    new_users = [u for u in users if u["boj_id"] != boj_id]

    if len(new_users) == len(users):
        print(f"'{boj_id}'를 찾을 수 없습니다.")
        return

    save_users(new_users)
    print(f"'{boj_id}' 삭제 완료!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python bot.py check     - 인증 현황 체크 및 디스코드 전송")
        print("  python bot.py reset     - 카운트 리셋 (새로 시작)")
        print("  python bot.py add <백준ID> <이름>  - 유저 추가")
        print("  python bot.py remove <백준ID>     - 유저 삭제")
        print("  python bot.py list      - 유저 목록")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        check_all_users()
    elif command == "reset":
        reset_counts()
    elif command == "add":
        if len(sys.argv) < 4:
            print("사용법: python bot.py add <백준ID> <이름>")
        else:
            add_user(sys.argv[2], sys.argv[3])
    elif command == "remove":
        if len(sys.argv) < 3:
            print("사용법: python bot.py remove <백준ID>")
        else:
            remove_user(sys.argv[2])
    elif command == "list":
        list_users()
    else:
        print(f"알 수 없는 명령어: {command}")
