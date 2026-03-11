<template>
  <div class="about">
    <div class="about-card surface-card">
      <h1>关于 vSkin</h1>
      <p>vSkin 是面向 Minecraft 社区的统一皮肤管理平台，支持角色管理、纹理托管、OAuth 授权与启动器集成。</p>
    </div>
  </div>
</template>

<style scoped>
@import "@/assets/styles/cards.css";

.about {
  min-height: calc(100vh - 180px);
  display: grid;
  place-items: center;
  padding: 20px;
}

.about-card {
  max-width: 760px;
  padding: 28px;
}

.about-card h1 {
  margin: 0 0 12px;
  color: var(--color-heading);
  font-weight: 760;
}

.about-card p {
  margin: 0;
  color: var(--color-text-light);
}
</style>
