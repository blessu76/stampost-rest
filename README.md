# stampost-rest — stampost.ipe.rest

도장 우체국 / Stampost 웹(ipe_web_kit · GitHub Pages). 문서 정본은 `_ipe/foundry/F-034_stampost/web/`.

## 로컬 빌드와 검사

Python 3.9 이상과 Node.js 20 이상이 필요합니다. 비공개 웹킷은 로컬에 설치하고 `vendor/ipe_web_kit.lock`으로 버전을 고정합니다.

```sh
repo="$(pwd)"
(cd ~/Developer/ipe_web_kit && python3 -m ipe_web_kit.vendor install "$repo" --tag v0.9.3)
python3 scripts/build_site.py
bash scripts/check.sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory public
```

사이트 카피는 `content/copy.json`, 게임 문구는 `content/play.json`, 개인정보 처리방침과 약관은 `content/policy.json`에서 편집합니다. 게임 규칙과 화면 스타일은 `assets/`에 있습니다. 변경 뒤 `public/`을 다시 생성합니다.

`assets/design/`의 토큰과 그림은 앱 레포 `foundry-f034` 커밋 `e9ce857`의 `assets/design/`에서 가져왔습니다.
앱 버전이 바뀌면 `scripts/build_site.py`의 `APP_VERSION`을 앱 `pubspec.yaml`에 맞춥니다.

## GitHub Pages

출력물은 `public/`에 있습니다. Pages 소스가 GitHub Actions로 설정되면 방장이 **Deploy Stampost to GitHub Pages** 워크플로를 직접 실행합니다. 예약 저널 발행 커밋은 같은 워크플로를 자동 실행합니다. CNAME은 `stampost.ipe.rest`입니다.

## 일일 저널

`content/journal/NN-글-주소.json`에 글의 12개 언어판을 넣습니다. Iris 검수를 받은 언어판에 `copy_review: iris`와 `copy_review_date: YYYY-MM-DD`를 각각 기록합니다. `python3 scripts/publish_post.py --dry-run`으로 다음 글을 확인할 수 있습니다. `content/journal/published.json`은 글 주소와 실제 KST 발행일을 기록합니다.

`ops/rest.ipe.stampost-publish.plist.template`은 매일 19:30 KST에 `ops/publish_daily.sh`를 실행하고 19:40·19:50에 다시 확인합니다. 한국 시간으로 설정된 발행 Mac에 발행 전용 클론·웹킷 클론·로그 파일의 절대 경로를 채워 등록합니다. 스크립트는 그린 게이트를 통과한 그날의 한 편과 정적 출력만 `main`으로 올립니다. 로그에 `QUEUE_LOW` 또는 `QUEUE_EMPTY`가 나오면 Iris 검수까지 마친 글을 보충합니다.
