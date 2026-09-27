# SoDam-RenderBoss-Codex — Codex 내장 이미지판

> 문서 기준: 2026-09-27 · 플러그인 버전: `0.2.0+codex.20260926162227` · 프로젝트 폴더 별칭: `SoDam-RenderBoss-Codex`

이 플러그인은 **Codex의 내장 이미지 생성 도구**로 건축 이미지를 새로 만들거나 기존 이미지를 편집할 때, 건물의 형태와 출입 요소를 지키도록 작업을 준비하고 결과를 점검합니다. **사용자 API 키와 Gemini는 필요하지 않습니다.** 단, Codex 로그인과 해당 작업에서 내장 이미지 생성 도구를 사용할 수 있는 권한·연결은 필요합니다. Python 명령만 실행해서 이미지를 생성하는 프로그램은 아닙니다.

**저장소:** 이 무키 버전의 배포 대상은 비공개 [`sodam-ai/SoDam-RenderBoss-Codex`](https://github.com/sodam-ai/SoDam-RenderBoss-Codex)입니다. 접근 권한이 있는 사용자만 내려받을 수 있습니다. 기존 [공개 원본](https://github.com/m174460635/architectural-render-guard)은 API 키를 요구하는 다른 버전이므로 혼동하지 마세요.

## 목차

1. [무엇을 할 수 있나요?](#features)
2. [준비물과 다운로드](#prerequisites)
3. [설치](#installation)
4. [빠른 시작](#quick-start)
5. [사용 방법과 명령어](#usage)
6. [작동 원리·워크플로우·아키텍처](#workflow)
7. [파일 위치](#files)
8. [보안과 데이터 흐름](#security)
9. [문제 해결](#troubleshooting)
10. [자주 묻는 질문](#faq)
11. [업데이트 요약](#updates)
12. [저작권·라이선스·상업적 사용](#legal)

<a id="features"></a>
## 1. 무엇을 할 수 있나요?

- **새 이미지:** 글로 건물 종류·분위기를 설명하면 Codex가 내장 도구로 이미지를 생성합니다.
- **기존 이미지 편집:** 첫 번째 이미지를 원본으로 사용하고, 두 번째 이후 이미지는 재료·색감·환경 등의 참고용으로 사용합니다.
- **보존 지시:** 매스, 층수, 지붕선, 카메라 시점, 창·문 위치와 수, 출입구, 계단, 램프, 난간, 간판 등을 바꾸지 않도록 프롬프트에 명시합니다.
- **부분 편집:** 원본과 크기가 같은 RGBA PNG 마스크의 **투명한 곳만 편집**하고, 불투명한 곳은 마지막에 원본 픽셀을 되돌립니다. 경계의 이음새는 눈으로 확인해야 합니다.
- **검수 자료:** 입력·출력 미리보기, 실제 출력 크기, 가로세로 비율 검사, 오류 목록을 남깁니다. 건물 형태가 정확히 유지됐는지는 사람이 원본과 비교해야 합니다.

**한계:** 기본값 `2K`는 생성 요청이지 출력 보장이 아닙니다. 실제 내장 도구 출력은 별도로 측정합니다. 2026-09-27 실제 생성·편집 점검에서 각각 `1672×941`이 나왔습니다. 정확한 픽셀 크기, 건축 요소의 완전한 동일성, 스트리밍 중간 이미지는 보장되지 않습니다. 필요하면 검수 후 별도 도구에서 업스케일할 수 있습니다.

<a id="prerequisites"></a>
## 2. 준비물과 다운로드

| 준비물 | 왜 필요한가 | 확인 또는 받는 곳 |
| --- | --- | --- |
| Windows PC와 파일 저장 공간 | 아래 명령은 Windows PowerShell 기준입니다. | 이미지와 결과를 저장할 폴더를 준비하세요. |
| Codex 계정·로그인 | 내장 이미지 도구를 사용합니다. API 키를 입력하지 않습니다. | [OpenAI Codex](https://openai.com/codex/)에서 시작하세요. 도구 접근은 계정·작업 환경에 따라 다릅니다. |
| Codex CLI | 아래 `codex plugin` 설치 명령을 실행합니다. 설치 후 데스크톱 앱에서 작업할 수 있습니다. | [공식 Codex CLI 안내](https://learn.chatgpt.com/docs/codex/cli)의 Windows 절차를 따르세요. |
| Python과 pip | 로컬 이미지 준비·검수 스크립트를 실행합니다. | [Python 공식 다운로드](https://www.python.org/downloads/)에서 설치하고, 설치 중 PATH 추가 옵션을 확인하세요. |
| Pillow | 이미지를 읽고 미리보기·마스크·PNG를 만듭니다. | 아래 `requirements.txt` 명령으로 설치합니다. |
| Git(선택) | 비공개 저장소를 명령으로 내려받거나 개발 변경을 올릴 때 사용합니다. | [Git for Windows](https://git-scm.com/download/win)에서 설치하세요. 압축본을 받는 일반 사용자에게는 필요하지 않습니다. |
| 사용할 이미지 | 기존 건물을 편집할 때만 필요합니다. | 본인 또는 사용 허가를 받은 PNG/JPEG 등의 이미지 파일을 준비하세요. |

**무키 프로젝트를 받는 방법:** 이 로컬 폴더를 사용하거나 비공개 저장소 접근 권한을 받은 뒤 `git clone https://github.com/sodam-ai/SoDam-RenderBoss-Codex.git`을 실행하세요. 접근 권한이 있다면 GitHub 저장소의 Code → Download ZIP으로 받을 수도 있습니다. 권한이 없다면 소유자가 제공한 패키지/압축본을 받으세요. 공개 원본을 무키 버전의 다운로드처로 쓰지 마세요. 패키지의 `.codex-plugin/plugin.json` 설명에 `Keyless`와 `Codex built-in`이 있는지 확인하고, 출처를 모르는 설치 스크립트는 실행하지 마세요.

PowerShell은 Windows의 명령 입력 창입니다. 시작 메뉴에서 **PowerShell**을 열고, 아래 코드 블록의 명령을 한 줄씩 붙여 넣으세요. 경로에 공백이 있으면 큰따옴표를 유지하세요. 예시의 `D:\...`는 이 PC의 현재 폴더이므로 다른 PC에서는 실제 경로로 바꿔야 합니다.

<a id="installation"></a>
## 3. 설치

### 3-1. 프로그램 확인과 Python 의존성 설치

```powershell
codex --version
python --version
python -m pip --version
Set-Location 'D:\AI_Dev_Work\2026y\26y_09m_28d_SoDam-RenderBoss-Codex'
python -m pip install -r requirements.txt
```

`codex` 또는 `python`을 찾지 못하면 해당 프로그램을 설치한 뒤 PowerShell을 새로 여세요. 이 프로젝트의 Python 의존성은 `Pillow>=10,<13`입니다. 일반 사용자는 `--init`의 자동 설치에 의존하기보다 위 명령으로 먼저 설치하세요. Python과 Pillow 설치에는 다운로드가 필요할 수 있습니다.

### 3-2. 현재 로컬 소스로 설치 가능한 마켓플레이스 만들기

```powershell
$marketplaceDir = Join-Path (Get-Location) ('outputs\keyless-marketplace-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python scripts/build_local_marketplace.py --out-dir $marketplaceDir
codex plugin marketplace add $marketplaceDir
codex plugin add architectural-render-guard@architectural-render-guard-keyless-local
codex plugin list
```

출력 폴더 이름에는 현재 시각을 넣어 기존 폴더와 겹치지 않게 합니다. 같은 초에 다시 실행해 폴더가 겹치면 이름을 바꿔 재시도하세요. `$marketplaceDir` 변수는 **같은 PowerShell 창**에서 계속 사용해야 합니다. 빌더 출력의 `marketplace_root`가 실제 등록 경로입니다. 빌더는 기존 폴더를 덮어쓰지 않습니다. 목록에서 `architectural-render-guard@architectural-render-guard-keyless-local`이 `installed, enabled`인지 확인하세요. 기존 공개 원본 항목과 구별해야 합니다. 설치 후 Codex에서 **새 작업**을 시작해 플러그인 스킬을 불러오세요. 다른 PC에서 패키지만 받은 경우 빌드 명령을 건너뛰고, 압축 해제된 패키지의 마켓플레이스 루트를 `codex plugin marketplace add`에 전달합니다.

### 3-3. 실행 가능 여부 확인

```powershell
python scripts/render_guard.py --init --no-install
python scripts/render_guard.py --list-formats
```

`--init`은 스킬 파일과 Pillow의 로컬 상태를 확인합니다. **내장 이미지 도구 사용 가능 여부는 확인하지 않습니다.** Codex의 새 작업에서 실제 이미지 생성 요청을 해야 그 부분을 확인할 수 있습니다. 인터넷 또는 계정 접근이 없는 상태에서 이 플러그인만으로 이미지를 만들 수는 없습니다.

### 3-4. 개발자가 테스트하고 비공개 저장소에 반영하기

```powershell
python -m unittest discover -s tests -v
python -m ruff check scripts tests
python -m compileall -q scripts tests
python scripts/build_local_marketplace.py --out-dir outputs/release-check
git status --short
git push origin builtin-imagegen
```

Ruff는 개발자용 검사 도구입니다. 없으면 `python -m pip install ruff`로 설치하세요. 일반 사용자에게는 필요하지 않습니다. 테스트가 실패하면 배포하지 말고 원인을 고치세요. 빌드 폴더가 이미 있으면 다른 이름을 쓰세요. `git push`는 개발자가 검수·커밋한 작업 branch에만 사용합니다. GitHub에서 `builtin-imagegen` → `main` PR을 열어 변경 파일과 테스트를 확인한 뒤 병합하세요. **`main`에 직접 push하거나 `scripts/publish.ps1`을 일반 사용자가 실행하지 마세요.** 이 프로젝트에는 사용자 API 키 환경 변수가 필요하지 않습니다. 설치 시 로그인은 Codex가 처리합니다.

`codex plugin marketplace add`/`codex plugin add`는 이 PC의 CLI `0.156.1` 도움말과 설치 상태에서 확인한 명령입니다. 다른 버전에서는 `codex plugin --help`를 확인하세요. 이 문서의 설치 절차는 CLI를 사용합니다. 데스크톱 앱만으로 설치하는 별도 절차는 검증하지 않았습니다.

<a id="quick-start"></a>
## 4. 빠른 시작: 처음 사용하는 사람

1. 위 설치를 끝내고 Codex에 로그인한 뒤 새 작업을 엽니다.
2. 기존 건물을 편집하려면 원본 이미지 파일을 첨부합니다. 새 건물 이미지를 만들려면 첨부하지 않아도 됩니다.
3. 아래 문장을 그대로 입력하고 `[ ]` 부분만 바꿉니다. 편집할 때는 층수·창문·문·계단·램프·간판 글자처럼 지켜야 할 요소를 구체적으로 적습니다.

> Architectural Render Guard로 이 건물 이미지를 실사화해 줘. [2층, 현재 창문과 문 수·위치, 중앙 출입구, 앞 계단, 오른쪽 램프, 간판 글자]는 그대로 유지하고, [맑은 낮의 자연스러운 재질과 조명]만 바꿔 줘. Codex 내장 이미지 생성만 사용하고 API 키나 Gemini는 사용하지 마. 결과의 실제 픽셀 크기와 바뀐 부분을 원본과 비교해 알려 줘.

4. Codex가 만든 이미지를 원본과 나란히 확인합니다. 창·문·계단·램프·간판이 바뀌었다면 **어느 부분이 다른지** 말하고 새 시도를 요청하세요. 새 이미지 생성이라면 건물 종류·층수·시점·재질을 설명하면 됩니다.
5. 검수된 이미지만 최종 사용하세요. `2K`로 요청했더라도 실제 크기는 결과 파일에서 확인합니다.

명령어를 직접 입력하지 않아도 Codex가 스킬을 따라 준비·생성·검수 절차를 수행할 수 있습니다. 아래 명령어는 수동 점검과 고급 사용을 위한 것입니다.

<a id="usage"></a>
## 5. 실행·사용 방법과 명령어

모든 예시는 프로젝트 최상위 폴더에서 PowerShell로 실행합니다. `--out-dir`의 결과는 프로젝트의 `outputs/`에 저장되며 Git 커밋 대상에서 제외됩니다. 이미지 경로는 자신의 파일 경로로 바꾸세요.

### 새 건물 이미지 만들기

```powershell
python scripts/render_guard.py --prepare --prompt '2층 동네 도서관, 정면 시점, 명확한 출입구와 계단 및 접근 램프, 실사, 낮의 자연광' --out-dir outputs/my-first-render --prefix library
```

위 명령은 **작업 JSON과 프롬프트만 준비**합니다. 출력된 `prompt_file`을 Codex에게 읽히고 내장 이미지 도구로 한 장을 생성하게 하세요. 내장 도구가 저장한 이미지 파일의 실제 경로를 확인한 후 다음처럼 마무리합니다.

```powershell
python scripts/render_guard.py --finalize --job outputs/my-first-render/library_attempt1_job.json --output 'C:\path\to\codex-generated.png'
```

### 기존 건물 편집하기

```powershell
python scripts/render_guard.py --prepare --image 'C:\images\building.png' --locked-subject '2층, 창문·문·중앙 출입구·앞 계단·오른쪽 램프·간판 유지' --style '실사, 밝은 낮, 석재와 목재 질감' --out-dir outputs/my-edit --prefix facade
```

첫 번째 `--image`가 편집 대상입니다. 참고 이미지를 더 주려면 같은 옵션 뒤에 경로를 이어 적습니다: `--image 'C:\images\building.png' 'C:\images\material.jpg'`. Codex에 **첫 번째 이미지만 건물 원본, 나머지는 스타일 참고**라고 알려 주세요. 첨부파일에 로컬 경로가 없다면 Codex 스킬이 대화의 이미지를 직접 참조할 수 있지만, `--prepare --image`는 실제 로컬 경로가 필요합니다.

### 부분 편집과 여러 번 시도하기

`--mask 'C:\images\mask.png'`를 추가할 수 있습니다. 마스크는 **원본과 같은 가로·세로 크기의 RGBA PNG**여야 하며, 투명 영역은 편집 가능, 불투명 영역은 원본 픽셀을 유지합니다. 반투명 영역의 결과와 경계 이음새는 직접 확인하세요. 기존 시도를 덮어쓰지 않고 다시 만들려면 `--attempt 2`, 다음은 `--attempt 3`을 지정합니다. 생성된 결과를 마무리할 때는 해당 시도의 `*_job.json`을 사용합니다.

### 주요 옵션

| 옵션 | 의미와 주의점 |
| --- | --- |
| `--prepare` / `--finalize` | 작업 준비 / Codex가 저장한 이미지의 마무리. 둘 중 한 동작을 선택합니다. |
| `--image PATH [PATH ...]` | 원본 1장과 선택적 참고 이미지. 편집에는 `--locked-subject`와 `--style` 또는 `--prompt`가 필요합니다. |
| `--prompt`, `--style`, `--locked-subject` | 만들 내용·바꿀 스타일·반드시 유지할 건물 요소를 설명합니다. |
| `--edit-area`, `--keep-text`, `--extra`, `--avoid` | 편집 영역, 그대로 남길 글자, 추가 요구, 피할 결과를 적습니다. |
| `--mask PATH` | 원본과 같은 크기의 RGBA PNG 부분 편집 마스크. |
| `--aspect-ratio` | 기본 `auto`; 지원값은 `--list-formats`에서 확인합니다. 새 이미지는 기본 `16:9`, 편집은 원본에 가장 가까운 지원 비율입니다. |
| `--resolution` | `native`, `1K`, `2K` 중 요청값. 기본 `2K`; 실제 크기는 보장하지 않습니다. |
| `--size WIDTHxHEIGHT` | 명시 크기를 **생성 후 실제 원본 출력과 대조**합니다. 도구가 그 크기로 생성하도록 강제하지 않습니다. 다르면 실패 상태로 기록합니다. |
| `--out-dir`, `--prefix`, `--attempt` | 결과 폴더·파일 앞부분·시도 번호. `prefix`는 영문/숫자로 시작하고 영문/숫자/`_`/`-`만 허용합니다. |
| `--preview-only --image PATH` | 생성 없이 입력 JPEG 미리보기만 만듭니다. |
| `--preview-max-edge`, `--preview-quality`, `--no-preview` | 미리보기 크기·품질 조정 또는 생략. |
| `--init --no-install`, `--list-formats` | 로컬 준비 상태 / 지원 비율과 참고 크기 확인. |

`--list-formats`의 원래 GPT 참고 크기(`2K 16:9`는 `2752×1536`)는 **내장 도구의 출력 보증값이 아닙니다**. `--size 2752x1536`을 입력하면 실제 결과가 다를 때 실패를 알려줄 뿐입니다. 결과 JSON의 `raw_output_dimensions`, `aspect_ratio_pass`, `requested_size_pass`, `errors`, `semantic_review`를 확인하세요. `requested_size_pass: null`은 `--size`를 지정하지 않아 검사 대상이 없다는 뜻입니다.

<a id="workflow"></a>
## 6. 작동 원리·워크플로우·아키텍처

```text
사용자 설명 + 선택적 원본·참고 이미지·마스크
  → Codex 스킬: 요구와 보존 요소 정리
  → render_guard.py --prepare: 입력 검사, 프롬프트·작업 JSON·미리보기 저장
  → Codex 내장 image_gen: 이미지 생성 또는 편집
  → render_guard.py --finalize: 실제 크기 측정, 선택적 마스크 합성, PNG·미리보기·기록 저장
  → Codex/사용자: 원본과 결과의 건물 형태·창문·문·계단·램프·간판 비교
  → 문제가 있으면 새 attempt로 반복
```

`scripts/builtin_guard.py`는 비율 선택·입력 크기 검사·프롬프트 작성의 보조 모듈입니다. `scripts/render_guard.py`가 사용자가 실행하는 명령입니다. 플러그인에는 웹 서버, DB, 로그인 서버, Gemini 연결 코드가 없습니다. Codex의 로그인·이미지 생성은 Codex 환경이 담당합니다. Python 스크립트는 내장 도구를 자동 호출하지 않으므로, 두 단계 사이에 Codex 작업이 반드시 있어야 합니다.

검사는 두 종류입니다. **자동 검사**는 파일 존재, 마스크 형식과 크기, 출력 비율, 명시 크기 등을 확인합니다. **육안 검사**는 실제 건축 요소와 글자가 유지됐는지를 원본과 비교합니다. `aspect_ratio_pass: true`만으로 건축 요소 보존을 입증할 수 없습니다.

<a id="files"></a>
## 7. 파일·문서 위치

| 프로젝트 최상위 폴더 기준 | 역할 |
| --- | --- |
| `README.md` / `README.html` | 동일한 한국어 안내의 Markdown / 웹페이지 파일. |
| `README.en.md` / `README.en.html` | 동일한 영어 안내의 Markdown / 웹페이지 파일. |
| `LICENSE` | 새 기여분에 적용되는 Apache License, Version 2.0 공식 원문. |
| `LICENSES/MIT-upstream.txt` / `NOTICE` | 원본 MIT 허락·저작권 표시 / 원본과 새 기여분의 출처 안내. |
| `requirements.txt` | Pillow 설치 조건. |
| `.codex-plugin/plugin.json` | 플러그인 이름·버전·설명. |
| `.agents/plugins/marketplace.json` | 비공개 저장소를 가리키는 설정. 설치에는 GitHub 접근 권한이 필요합니다. |
| `skills/architectural-render-guard/SKILL.md` | Codex 에이전트의 이미지 작업 순서. |
| `scripts/render_guard.py` / `scripts/builtin_guard.py` | 사용자 CLI / 보조 로직. |
| `scripts/build_local_marketplace.py` | 로컬 설치 패키지 생성. |
| `scripts/publish.ps1` | 개발자용 발행 스크립트. **일반 설치에 실행하지 마세요.** 배포는 작업 branch push와 PR 검토를 사용하세요. |
| `tests/` | 자동 테스트. |
| `outputs/<작업 이름>/` | 작업 JSON, 프롬프트, 결과 PNG, manifest JSON, `_previews/` JPEG. `outputs/`는 Git에서 제외됩니다. |

HTML 문서는 브라우저로 열어 읽을 수 있습니다. **HTML을 열어도 플러그인이 실행되거나 이미지가 생성되지는 않습니다.** 로컬 패키지 빌더는 핵심 플러그인 파일과 네 README 문서, `LICENSE`, 원본 MIT 고지, `NOTICE`를 함께 포함합니다. 폴더를 옮기면 기존 작업 JSON에는 이전 절대경로가 남을 수 있으므로 새 `--prepare` 작업을 만드세요.

<a id="security"></a>
## 8. 보안과 데이터 흐름

- 사용자 입력 이미지·참고 이미지·마스크의 **로컬 경로**가 작업 JSON에 기록됩니다. 프롬프트·미리보기·최종 PNG·manifest도 지정한 로컬 `outputs/`에 저장됩니다. 폴더 이름이나 이미지에 개인 정보가 있으면 JSON에도 경로가 남을 수 있습니다.
- 이미지 생성 단계에서는 Codex 내장 도구에 사용자 설명과 선택한 이미지가 전달됩니다. 이 과정의 계정 권한·데이터 처리·사용 한도는 적용되는 [OpenAI 약관](https://openai.com/policies/row-terms-of-use/), [서비스 약관](https://openai.com/policies/service-terms/) 및 계정 설정을 확인하세요. **API 키가 필요 없다는 말은 이미지가 오프라인에서 처리된다는 뜻이 아닙니다.**
- 이 저장소의 Python 이미지 경로에는 API 키 읽기, 외부 이미지 API 요청, Gemini 호출이 없습니다. 다만 `python -m pip install -r requirements.txt`는 패키지를 다운로드하고, 개발자용 `scripts/publish.ps1`은 별도의 GitHub 발행 동작을 합니다.
- `.env`, `*.log`, `outputs/`는 `.gitignore`에서 제외됩니다. **`outputs/` 밖의 이미지까지 자동 제외되지는 않습니다.** 무시 규칙만으로 모든 비밀정보 유출을 막을 수 없으므로 공유·커밋 전 파일 목록과 이미지의 내용·간판·인물·주소를 직접 확인하세요. 민감한 고객 자료는 업로드 권한과 계정 데이터 정책을 먼저 확인하세요.
- 같은 이름의 기존 결과와 작업을 덮어쓰지 않도록 설계했습니다. 완료된 `manifest`의 `errors`가 비어 있어도 시각 검수는 별도입니다.

<a id="troubleshooting"></a>
## 9. 문제·오류 대처

| 증상 | 확인과 해결 |
| --- | --- |
| `codex` 또는 `python` 명령을 찾을 수 없음 | 공식 설치를 완료하고 PowerShell을 새로 연 뒤 `codex --version`, `python --version`을 다시 실행하세요. |
| `Pillow is missing` / `No module named PIL` | 프로젝트 폴더에서 `python -m pip install -r requirements.txt`를 실행하세요. 설치에 사용한 `python`과 실행에 사용한 `python`이 같아야 합니다. |
| 플러그인이 목록에 없거나 API 키를 요청함 | `codex plugin list`에서 이름 끝이 `@architectural-render-guard-keyless-local`인지 확인하세요. 공개 항목과 혼동하지 말고 새 Codex 작업을 시작하세요. |
| 내장 이미지 도구를 사용할 수 없음 | Codex 로그인, 계정·작업의 이미지 도구 접근, 연결 상태를 확인하세요. 이 플러그인에는 API 키나 Gemini 대체 경로가 없습니다. |
| `Destination already exists` / `Job already exists` / `Preview already exists` | 출력 폴더·`--prefix`·`--attempt`를 새 값으로 지정하세요. 기존 결과를 지우거나 덮어쓰지 마세요. |
| `Input image does not exist` / 폴더 이동 후 실패 | 실제 이미지 경로를 확인하고 현재 위치에서 새 `--prepare`를 실행하세요. 이전 작업 JSON의 절대경로를 그대로 재사용하지 마세요. 로컬 마켓플레이스 폴더를 옮겼다면 새 위치를 `codex plugin marketplace add`로 다시 등록하고 플러그인을 설치한 뒤 새 작업을 여세요. |
| 마스크 RGBA·크기 오류 | 투명도가 있는 RGBA PNG로 저장하고 원본 이미지와 픽셀 가로·세로 크기를 같게 하세요. |
| 결과가 `1672×941`이고 요청은 `2752×1536` | `2K` 참고 크기는 보장되지 않습니다. 실제 크기를 확인하고 필요하면 검수 후 별도 업스케일을 사용하세요. 명시 `--size` 불일치는 실패로 기록됩니다. |
| 비율·크기 검사 실패 또는 `errors`가 있음 | 실패한 시도를 채택하지 말고 출력과 manifest를 확인한 뒤 새 `--attempt`로 다시 요청하세요. |
| 창문·문·계단·글자가 달라짐 | 원본과 눈으로 비교해 변경 지점을 구체적으로 적고 재생성하세요. 마스크 사용 시 경계도 확인하세요. 자동 검사는 의미적 동일성을 보증하지 않습니다. |

문제가 생기면 **실패 메시지와 작업 JSON의 필드 이름**을 확인하되, 고객 이미지·개인정보·계정 정보·비밀번호는 공개 이슈나 채팅에 그대로 올리지 마세요.

<a id="faq"></a>
## 10. FAQ

**Q. API 키가 정말 없어도 되나요?** 네. 이 로컬 버전은 사용자 API 키와 Gemini 없이 Codex 내장 이미지 도구를 사용하도록 구성됐고 실제 생성까지 확인했습니다. Codex 로그인과 이미지 도구 접근은 필요합니다.

**Q. 완전히 무료이고 오프라인인가요?** 그렇게 보장하지 않습니다. API 키가 없다는 것과 계정 요금·사용 한도·인터넷 연결 여부는 별개입니다. 현재 계정 조건은 Codex에서 확인하세요.

**Q. 어디서 이 버전을 받나요?** 접근 권한이 있다면 비공개 `sodam-ai/SoDam-RenderBoss-Codex`에서 받으세요. 공개 원본은 다른 버전입니다. 로컬 마켓플레이스 설치 후 manifest 설명을 확인하세요.

**Q. 왜 `--prepare`만으로 이미지가 안 나오나요?** Python은 작업을 준비하고, 실제 생성은 Codex 내장 이미지 도구가 수행합니다. 생성 후 `--finalize`가 결과를 검수 파일로 만듭니다.

**Q. 2K와 모든 건축 요소를 보장하나요?** 아니요. 2K는 요청이고, 형태 보존은 프롬프트와 사람이 하는 비교 검사에 의존합니다. 마스크의 불투명 영역만 로컬 픽셀 복원 대상입니다.

**Q. 휴대전화에서 바로 실행되나요?** 이 문서의 설치·Python·PowerShell 절차는 Windows PC용입니다. 모바일 단독 설치와 화면 사용은 검증하지 않았습니다. 완성 이미지를 휴대전화에서 보는 것은 별개입니다.

**Q. 이미지를 상업적으로 써도 되나요?** 아래의 코드 Apache/MIT 허락과 **생성 이미지·원본·참고 자료의 권리**는 다릅니다. 사용 권한·상표·인물 동의·고객 계약·적용되는 OpenAI 약관을 검토해야 합니다.

<a id="updates"></a>
## 11. 업데이트 요약

<details>
<summary>펼쳐 보기: 현재 로컬 무키 버전에서 달라진 점</summary>
<div>
<p>기존 외부 이미지 API/Gemini 경로 대신 Codex 내장 이미지 생성 도구를 사용하는 준비 → 생성 → 마무리 흐름으로 바꿨습니다. 사용자 API 키는 요구하지 않습니다.</p>
<ul><li>새 이미지와 기존 이미지 편집, 여러 참고 이미지, 건물 보존 지시, RGBA 마스크 합성, 입력·출력 미리보기, 시도별 결과 기록을 제공합니다.</li><li>실제 출력 비율·크기를 기록하고 명시한 픽셀 크기가 다르면 실패로 표시합니다. 내장 도구의 정확한 2K 크기와 의미적 보존은 보장하지 않습니다.</li><li>비공개 저장소 배포, Apache 2.0 새 기여분 라이선스, 원본 MIT 고지 보존, 로컬 패키지 빌더와 자동 테스트를 반영했습니다.</li></ul>
</div>
</details>

<a id="legal"></a>
## 12. 저작권·라이선스·상업적 사용

**프로젝트 코드·문서:** 새 기여분은 **Apache License, Version 2.0**이며 권리자 표시는 `Copyright 2026 SoDam AI Studio`입니다. 원본 `architectural-render-guard`의 `Copyright (c) 2026 m174460635`와 **MIT License**는 [`LICENSES/MIT-upstream.txt`](LICENSES/MIT-upstream.txt)에 그대로 보존했습니다. [`LICENSE`](LICENSE)는 Apache 원문이고 [`NOTICE`](NOTICE)는 출처를 설명합니다. 재배포할 때 Apache 본문과 기존 MIT 고지를 함께 보존하고, 변경 파일·출처를 표시해야 합니다. 두 라이선스 모두 보증·책임 제한을 포함합니다.

**쉽게 말해:** 두 라이선스의 조건을 지키면 코드·문서를 개인 작업, 교육, 회사 업무, 포크, 수정, 재배포, 유료 판매, 서비스 운영, 고객 납품에 사용할 수 있습니다. 복제·수정해 전달할 때 `LICENSE`, `LICENSES/MIT-upstream.txt`, `NOTICE`를 함께 보존하세요. 이미지·외부 서비스의 권리는 아래처럼 별도입니다.

**설치 의존성:** `requirements.txt`의 유일한 Python 의존성은 `Pillow>=10,<13`입니다. Pillow는 이 프로젝트의 Apache/MIT와 별도인 [MIT-CMU 라이선스](https://github.com/python-pillow/Pillow/blob/main/LICENSE)를 사용합니다. 현재 로컬 확인 버전은 12.3.0입니다. Pillow 또는 이를 포함한 실행 파일·설치 패키지를 재배포할 때는 해당 버전의 저작권·허락 고지와 번들된 구성요소의 라이선스를 확인해 동봉하세요. 허락 없는 저작자 이름의 홍보 사용도 피하세요. 버전 범위 안의 향후 설치 버전과 그 바이너리 구성은 여기서 권리를 보증하지 않습니다.

**Codex 서비스·요금:** 이 플러그인에는 사용자 API 키가 필요하지 않지만, Codex 계정의 이미지 도구 접근 권한·사용 한도·요금이 무료 또는 무제한이라는 뜻은 아닙니다. 사용 전 자신의 계정에 적용되는 최신 요금제·서비스 약관·이미지 생성 정책을 확인하세요. 이 저장소는 외부 API·모델·SDK 비용을 대신 지불하거나 이용권을 제공하지 않습니다.

**별도로 확인할 권리:** 이 프로젝트의 Apache/MIT 허락은 사용자가 넣은 원본·참고 이미지, 제3자 건축 설계·도면·상표·간판·인물, 생성 결과, Python/Pillow, Codex/OpenAI 서비스의 권리와 약관을 대신 허락하지 않습니다. 사용자가 입력 자료를 제공할 권리와 공개·수정·상업적 이용 권한을 확인해야 합니다. OpenAI의 [이용 약관](https://openai.com/policies/row-terms-of-use/)은 적용 법률이 허용하는 범위에서 사용자와 OpenAI 사이의 출력 권리 관계를 설명하지만, **제3자 권리나 결과의 독창성까지 보증하지 않습니다**. 사용 지역·계정 종류·계약에 맞는 [서비스 약관](https://openai.com/policies/service-terms/)과 정책도 확인하세요. 고객 납품, 광고, 판매 전에는 간판 문구·상표·초상권·건축 설계 저작권과 계약 범위를 검토하세요.

**자료별 점검:** 현재 코드 패키지에는 이미지·아이콘·폰트·영상·음원·샘플 계정이 포함되지 않습니다. 로컬 `outputs/`는 Git에서 제외되지만 생성 이미지·미리보기·로그가 남을 수 있습니다. 이 자료를 공유하거나 납품하기 전에는 원본·참고 이미지, 도면·템플릿·프롬프트, 화면 캡처, 생성물의 출처·상업적 이용 조건을 확인하고 개인정보·고객사 정보·비공개 자료·상표·간판을 검수하세요. AI 생성 코드·문서·이미지도 최종 사용 전에 출처, 저작권, 제3자 저작물과의 유사성, 상업적 이용 조건을 확인해야 합니다. 다른 API·모델·SDK·스톡 자료·폰트·아이콘을 추가하면 각각의 요금제·약관·라이선스를 별도로 확인하세요.

**법무/전문가 검토 필요:** 원본 MIT 코드에서 수정된 파일과 새 Apache 2.0 기여분의 정확한 권리·고지 범위, 표시된 기여자의 권한, 고객 자료의 업로드 허락, 생성물의 제3자 권리, 실제 납품 계약·관할 법률은 저장소 파일만으로 확정할 수 없습니다. 공개 배포·판매·고객 납품 전에 해당 자료와 계약을 확인하세요.

**금지·주의:** 타인의 권리를 침해하는 입력·사용, 허가 없는 인물 이미지 활용, OpenAI 서비스의 제한 우회는 허용되지 않을 수 있습니다. 라이선스의 보증 없음은 불법 사용을 허락하는 문구가 아닙니다. 이 문서는 일반 안내이며 법적 효력을 보장하지 않습니다. 실제 상업 배포·분쟁 판단은 사용자 책임으로 관련 계약을 확인하고 필요하면 변호사에게 확인받으세요.
