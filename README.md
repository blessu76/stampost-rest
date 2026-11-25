# stampost-rest — stampost.ipe.rest

도장 우체국 / Stampost 웹(ipe_web_kit · GitHub Pages). 문서 정본은 `_ipe/foundry/F-034_stampost/web/`.

## 로컬 빌드와 검사

Python 3.9 이상과 Node.js 20 이상이 필요합니다. 비공개 웹킷은 로컬에 설치하고 `vendor/ipe_web_kit.lock`으로 버전을 고정합니다.

```sh
repo="$(pwd)"
(cd ~/Developer/ipe_web_kit && python3 -m ipe_web_kit.vendor install "$repo" --tag v0.7.3)
python3 scripts/build_site.py
bash scripts/check.sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory public
```

사이트 카피는 `content/copy.json`, 게임 문구는 `content/play.json`에서 편집합니다. 게임 규칙과 화면 스타일은 `assets/`에 있습니다. 변경 뒤 `public/`을 다시 생성합니다.

`assets/design/`의 토큰과 그림은 앱 레포 `foundry-f034` 커밋 `e9ce857`의 `assets/design/`에서 가져왔습니다.
앱 버전이 바뀌면 `scripts/build_site.py`의 `APP_VERSION`을 앱 `pubspec.yaml`에 맞춥니다.

## GitHub Pages

출력물은 `public/`에 있습니다. Pages 소스가 GitHub Actions로 설정되면 방장이 **Deploy Stampost to GitHub Pages** 워크플로를 직접 실행합니다. CNAME은 `stampost.ipe.rest`입니다.
