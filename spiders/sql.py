import ast
from datetime import datetime
from pathlib import Path

import pymysql


def parse_date(value: str):
    """Try to parse date; return None if invalid."""
    if not value:
        return None
    value = value.strip().replace("/", "-")
    try:
        # 长度 4 的年份也接受
        if len(value) == 4:
            return f"{value}-01-01"
        # 截断到前 10 位，兼容 '2022-05-20' 这样的格式
        return datetime.fromisoformat(value[:10]).date()
    except Exception:
        return None


def load_records():
    """Load movie dicts from ur.txt safely."""
    path = Path(__file__).resolve().parent / "ur.txt"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                # 每行是一个 list[dict]
                data = ast.literal_eval(line)
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    continue
                for item in data:
                    if isinstance(item, dict):
                        yield item
            except Exception as exc:
                print(f"解析行失败: {exc}")
                continue


def main():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        passwd="zxu7696638",
        db="django_1",
        charset="utf8mb4",
    )
    cursor = conn.cursor()

    sql = """
        INSERT INTO myapp_movie
        (title, score, date, poster, actors, region, `type`, summary)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    for item in load_records():
        title = item.get("title", "")
        score = item.get("score") or (item.get("rating") or [None])[0]
        release_date = parse_date(item.get("release_date", ""))
        poster = item.get("cover_url", "")
        actors = " ".join(item.get("actors", []))
        region = " ".join(item.get("regions", []))
        movie_type = " ".join(item.get("types", []))
        summary = item.get("summary", "")

        try:
            cursor.execute(
                sql,
                (
                    title,
                    score,
                    release_date,
                    poster,
                    actors,
                    region,
                    movie_type,
                    summary,
                ),
            )
        except Exception as exc:
            print(f"插入失败 {title}: {exc}")
            continue

    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()