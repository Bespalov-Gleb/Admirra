<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">
    <div class="flex flex-1 items-center">
      <div class="w-full grid grid-cols-1 lg:grid-cols-[7fr_4fr_4fr] gap-[15px] text-[15px]">

        <!-- Info card -->
        <div class="bg-white rounded-[15px] p-[30px]">
          <h3 class="text-[30px] font-semibold leading-[1.25] text-[#171717] dark:text-white mb-[15px]">
            Выберите рекламный канал<br />
            <span class="gradient-text">для сбора всей статистики</span>
          </h3>
          <p class="text-[15px] font-medium leading-[1.35] text-[rgba(105,105,105,0.56)] mb-[30px]">
            Если у вас несколько рекламных каналов в разных системах,<br />
            дополнительные рекламные системы Вы сможете подключить уже&nbsp;в&nbsp;панели отчета
          </p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-y-[10px]">
            <div class="bg-white border border-[rgba(105,105,105,0.1)] rounded-[15px]">
              <div class="p-[30px] font-medium leading-[1.35] text-[rgba(44,44,44,0.8)]">
                <span class="text-[#c7ae8d]">Для подключения Яндекс.Директ</span><br />
                Вы должны иметь доступ к&nbsp;рекламному кабинету Яндекс.Директа и Яндекс.Метрики
              </div>
            </div>
            <div class="bg-white border border-[rgba(105,105,105,0.1)] rounded-[15px] pl-[5px]">
              <div class="p-[30px] font-medium leading-[1.35] text-[rgba(44,44,44,0.8)]">
                <span class="text-[#9cadc2]">Для подключения VK ADS</span><br />
                у вас должен быть агентский или личный доступ к рекламному кабинету
              </div>
            </div>
          </div>
        </div>

        <!-- Яндекс.Директ card -->
        <div class="channel-card channel-card--yandex">
          <div class="mb-[16px]">
            <img width="47" src="/admirra/img/icons/yandex-direct.png" alt="Yandex Direct" />
          </div>
          <div class="mt-auto flex flex-col">
            <div class="channel-card__title">Яндекс.Директ</div>
            <button class="channel-btn" @click="goToWizard('YANDEX_DIRECT')">
              <span class="text-[#c7ae8d]">Авторизоваться</span>
            </button>
          </div>
        </div>

        <!-- ВК Ads card -->
        <div class="channel-card channel-card--vk">
          <div class="mb-[16px]">
            <img width="47" src="/admirra/img/icons/vk-ads.png" alt="VK Ads" />
          </div>
          <div class="mt-auto flex flex-col">
            <div class="channel-card__title">ВК Ads Manager</div>
            <button class="channel-btn" @click="goToWizard('VK_ADS')">
              <span class="text-[#b2c5db]">Авторизоваться</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToWizard(platform) {
  router.push({ path: '/integrations/wizard', query: { platform } })
}
</script>

<style scoped>
.gradient-text {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.channel-card {
  height: 100%;
  padding: 30px;
  border-radius: 15px;
  display: flex;
  flex-direction: column;
}
.channel-card--yandex { background-color: #fff2e1; }
.channel-card--vk     { background-color: #deedff; }

.channel-card__title {
  font-size: 20px;
  color: #515151;
  font-weight: 500;
  margin-bottom: 23px;
}

.channel-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60px;
  padding: 10px 25px;
  font-size: 15px;
  font-weight: 500;
  line-height: 1.1;
  border: none;
  border-radius: 23px;
  cursor: pointer;
  background: #fff;
  position: relative;
  overflow: hidden;
  transition: transform 0.75s, background-color 0.5s;
}
.channel-btn:hover { transform: scale(1.03); background-color: #f5f5f5; }
.channel-btn:active { transform: scale(0.97); transition: transform 0s; }
</style>
