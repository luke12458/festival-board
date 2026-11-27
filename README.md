# 文化祭の二択会議
## Macで開く
展開したフォルダで以下を実行し、表示されたURLを開く。初回は「議題を出す」から投稿する。
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run
```
開発時の保存先はinstance/board.db。以前の静的デモの端末内投稿は移行しない。

## Azureの初期設定
1. Azure PortalでLinuxのWebアプリを作成し、コード・Python 3.12・Free F1を選ぶ。F1を選べないときは有料プランへ進まず学校に確認する。
2. 同じリソースグループに汎用v2 Standard LRSストレージアカウントを作成。ストレージの容量・操作には料金が設定されているため、学校契約または学生クレジットの範囲を確認する。Blobのコンテナー「pictures」を非公開で作成し、テーブル「FestivalBoard」を作成する。
3. Webアプリの「ID」でシステム割り当てをオン。ストレージのアクセス制御（IAM）でそのIDに「Storage Blob Data Contributor」「Storage Table Data Contributor」を付与する。
4. Webアプリの環境変数に STORAGE_ACCOUNT（ストレージアカウント名）、SECRET_KEY（下記で生成する固定のランダム値）、SCM_DO_BUILD_DURING_DEPLOYMENT（true）を設定。スタートアップコマンドは gunicorn --bind=0.0.0.0:8000 app:app 。保存して再起動する。
```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## GitHubから自動公開（OIDC）
1. GitHubで空のPublicリポジトリを作る。Entra IDでデプロイ用アプリを登録し、そのアプリのフェデレーション資格情報にGitHub Actions、対象の所有者・リポジトリ・Branch「main」を指定する。WebアプリのIAMでこのアプリのサービスプリンシパルに「Website Contributor」を付与する。学校側で権限が必要な場合は担当者に設定を依頼する。
2. GitHubリポジトリの Settings → Secrets and variables → Actions → Variables に AZURE_CLIENT_ID（デプロイ用アプリのクライアントID）、AZURE_TENANT_ID、AZURE_SUBSCRIPTION_ID、AZURE_WEBAPP_NAME を登録。
3. 展開フォルダ直下で次を実行する。YOUR-ACCOUNT と YOUR-REPO は作った公開リポジトリに合わせる。
```sh
git init -b main
git add .gitignore .github app.py storage.py templates static requirements.txt requirements.md README.md
git commit -m "Add festival voting board"
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPO.git
git push -u origin main
```
4. Actionsの「Publish festival board」が成功したらAzure PortalのWebアプリ「概要」から既定のドメインを開く。画像付き投稿を作り、別ブラウザーで同じ画像と投票結果を確認する。Teamsにrequirements.md・公開サイトURL・GitHub URLを提出する。

https://festival-board-luke12458-bgexgkf0czd2fsbh.japaneast-01.azurewebsites.net/
