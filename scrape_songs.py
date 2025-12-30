import requests
from bs4 import BeautifulSoup

def get_static_song_names(page_url, song_selector):
    """
    获取静态网页中的所有歌曲名
    :param page_url: 目标页面URL
    :param song_selector: 歌曲名元素的CSS选择器（需根据实际页面调整）
    :return: 歌曲名列表（最多200条）
    """
    # 请求头，模拟浏览器访问，避免被反爬
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # 发送GET请求获取页面内容
        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()  # 若请求失败（状态码≥400），抛出异常
        response.encoding = response.apparent_encoding  # 自动识别编码，避免乱码
        
        # 解析页面
        soup = BeautifulSoup(response.text, "html.parser")
        # 根据CSS选择器获取所有歌曲名元素
        song_elements = soup.select(song_selector)
        
        # 提取歌曲名并去重、过滤空值，限制最多200条
        song_names = []
        for elem in song_elements:
            song_name = elem.get_text(strip=True)  # 去除首尾空格和换行符
            if song_name and song_name not in song_names:
                song_names.append(song_name)
                if len(song_names) >= 200:  # 达到200首则停止
                    break
        
        return song_names
    except Exception as e:
        print(f"获取失败：{str(e)}")
        return []

# -------------------------- 配置参数（需根据你的实际页面修改） --------------------------
TARGET_URL = "https://www.bilibili.com/video/BV1QX4y1d7tr/?spm_id_from=333.1007.top_right_bar_window_history.content.click&vd_source=c581a60154524ce715dc7688d326cd48"  # 替换成实际页面地址
# 示例选择器：根据页面结构调整，比如 ".song-item .name"、"ul.song-list li a" 等
# 注意：这里应当填写一个 CSS 选择器（例如 'div.title-txt' 或 '.title-txt'），而不是 HTML 片段
SONG_CSS_SELECTOR = 'div.title-txt'  # 关键：需通过浏览器F12开发者工具确认（示例：选择器应为 CSS 选择器，如 'div.title-txt'）
# -------------------------------------------------------------------------------------

# 执行获取
if __name__ == "__main__":
    song_list = get_static_song_names(TARGET_URL, SONG_CSS_SELECTOR)
    # 打印结果
    print(f"共获取到 {len(song_list)} 首歌曲：")
    for index, song_name in enumerate(song_list, start=1):
        print(f"{index}. {song_name}")
    # 保存到本地文件（可选）
    with open("静态页面歌曲列表.txt", "w", encoding="utf-8") as f:
        for song in song_list:
            f.write(song + "\n")
    print("歌曲列表已保存到 静态页面歌曲列表.txt")