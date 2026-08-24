# Yogesh Streamer Official Plugin Repository

This is the official extension repository for **Yogesh Streamer**.

---

## 🔌 Repository URL

Add this URL in **Yogesh Streamer > Settings > Extensions > Add Repository**:

```text
https://raw.githubusercontent.com/shahrukh-hack/yogesh-streamer-plugins/master/repo.json
```

Or simply use the built-in verified provider listing inside the app.

---

## 🛠️ How to Add or Improve a Plugin

1. Create a new provider class extending `MainAPI` in `src/`.
2. Increment the `version` number in `plugins.json`.
3. Push to `master`. GitHub Actions will automatically compile the `.cs3` module and update your users instantly!
