if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/js/sw.js").catch(() => {
      // 서비스워커 등록 실패는 앱 사용에 지장이 없으므로 조용히 무시
    });
  });
}
