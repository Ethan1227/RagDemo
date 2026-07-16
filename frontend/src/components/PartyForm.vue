<template>
  <div class="party-form">
    <el-row :gutter="10">
      <el-col :span="6">
        <el-input v-model="party.name" placeholder="姓名/名称" size="default" />
      </el-col>
      <el-col :span="7">
        <el-input v-model="party.id_card" placeholder="身份证号/统一社会信用代码" />
      </el-col>
      <el-col :span="6">
        <el-input v-model="party.address" placeholder="住所" />
      </el-col>
      <el-col :span="4">
        <el-input v-model="party.phone" placeholder="联系方式" />
      </el-col>
      <el-col :span="1">
        <el-button link type="danger" @click="$emit('remove')" title="移除">
          <el-icon><Delete /></el-icon>
        </el-button>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
defineProps({
  party: { type: Object, required: true },
  index: { type: Number, default: 0 },
})
defineEmits(['remove'])
</script>

<style scoped>
.party-form {
  margin-bottom: 10px;
}
</style>
