# Automated MongoDB Uploader with GUI

##화면 구성과 주요 기능

![GUI](https://user-images.githubusercontent.com/47588410/229041766-7aba9c53-aa1d-47bb-a7d5-6a500bfdb39a.png)

### 1. 자동저장 및 업로드
![allright](https://user-images.githubusercontent.com/47588410/229044321-c98000d4-b5e1-4370-a8c5-6480d1154bc1.png)
* 자동저장 기능이 활성화되면, 원의 색깔이 초록색으로 바뀌며, 하위 디렉토리에 있는 양식에 맞는 엑셀 파일들의 변화를 감지해 실시간으로 DB에 반영합니다.

### 2. 수동저장 및 업로드
![manusave](https://user-images.githubusercontent.com/47588410/229044738-bb13c168-3493-4f82-9ef9-5d61e71358c5.png)

* 마지막 저장 시각은 프로그램이 켜진 동안 업로드 동작이 일어날 때마다 업데이트 됩니다. 이는 자동저장을 포함합니다.

![image](https://user-images.githubusercontent.com/47588410/229044891-0205604a-a07b-4b25-80f1-2607978c0f54.png)

* 수동저장은 마지막 저장 시의 상태와 현재 상태를 비교해, 업데이트가 일어난 문서를 찾고, DB에 반영합니다. 자동저장, 수동저장 모두 업데이트 후 위와 같은 Log를 출력합니다.

![image](https://user-images.githubusercontent.com/47588410/229045079-317fa346-32f1-4d31-af71-2d2078a765d6.png)

* 온라인DB에 있는 데이터를 기준으로, 로컬의 엑셀 파일들을 동기화 합니다. Pull에 해당합니다.


### 3. DB 검색 및 수정
![search](https://user-images.githubusercontent.com/47588410/229042830-968be895-140c-4d8b-a149-afc1ad8857f2.png)
![docnum](https://user-images.githubusercontent.com/47588410/229043150-2fdf1f23-b972-4b94-b0c0-568fe4d95758.png)

* 검색을 통해 DB에 업로드된 문서들을 확인합니다. Reserved Query로 '#'이 존재하며, 이를 통해 업로드된 총 문서 수를 확인할 수 있습니다.


### 4. 문서 상세보기
![example](https://user-images.githubusercontent.com/47588410/229043814-d1f04a6f-febd-4b23-b855-1bab577cb2ad.png)
* 문서의 상세 내용을 보고 수정할 수 있습니다. 수정 시, 온라인 DB와 로컬에 존재하는 엑셀 파일(있다면)을 입력한대로 수정합니다.

* 다운로드를 통해 온라인에 있는 데이터를 엑셀 형식으로 받을 수 있습니다. 해당 문서가 로컬에 존재하면 덮어쓰고, 아니라면 새로 다운로드합니다.

* 삭제버튼을 누르면 온라인 상의 데이터만 삭제합니다.
