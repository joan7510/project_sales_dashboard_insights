# GitHub Upload Steps

Use these commands from this folder:

```bash
cd /Users/qionghuang/Documents/data_analysis
```

## 1. Initialise Git

```bash
git init
```

## 2. Check What Will Be Uploaded

```bash
git status --short
```

Expected code/docs files include:

```text
.gitignore
GITHUB_UPLOAD_STEPS.md
README.md
convert_csv_to_python_data.py
generate_static_report.py
requirements.txt
streamlit_app.py
update_item_sales_categories.py
reports/README.txt
```

Data and generated report files should be ignored, including:

```text
alphago_fitness/
combined_data/
python_data/
*.csv
*.pkl
reports/*.html
reports/*.pdf
phase*_cleanup_log.txt
```

## 3. Stage Code Only

```bash
git add .gitignore GITHUB_UPLOAD_STEPS.md README.md requirements.txt \
  convert_csv_to_python_data.py generate_static_report.py streamlit_app.py \
  update_item_sales_categories.py reports/README.txt
```

## 4. Confirm No Data Is Staged

```bash
git diff --cached --name-only
```

Make sure no files ending in `.csv`, `.pkl`, `.pdf`, `.html`, `.xlsx`, `.numbers`, or raw data folders are listed.

## 5. Commit

```bash
git commit -m "Initial dashboard analysis code"
```

## 6. Connect To GitHub

GitHub repository:

```text
https://github.com/joan7510/project_sales_dashboard_insights.git
```

```bash
git branch -M main
git remote add origin https://github.com/joan7510/project_sales_dashboard_insights.git
git push -u origin main
```

Example repo URL formats:

```text
https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git@github.com:YOUR_USERNAME/YOUR_REPO_NAME.git
```

## Future Updates

Before each push, check what is staged:

```bash
git status --short
git diff --cached --name-only
```

Then commit and push:

```bash
git add README.md *.py requirements.txt reports/README.txt
git commit -m "Update dashboard workflow"
git push
```
