<template>
  <el-drawer :visible.sync="dialogVisible" direction="rtl" size="80%" :wrapperClosable="false" :withHeader="false">
    <div class="custom-header">
      <div class="header-left">
        <h3 class="bold-title">{{ $t('skillDialog.title') }}</h3>
        <span class="count-tip">{{ $t('skillDialog.skillsCount', { count: localSkills.length }) }}</span>
      </div>
      <button class="custom-close-btn" @click="closeDialog">×</button>
    </div>

    <div class="skill-manager">
      <!-- 左侧：技能列表 -->
      <div class="skill-column">
        <div class="column-header">
          <h4 class="column-title">{{ $t('skillDialog.skillList') }}</h4>
          <el-button type="primary" size="small" @click="addSkill">
            {{ $t('skillDialog.add') }}
          </el-button>
        </div>
        <div class="skill-list">
          <div v-if="localSkills.length">
            <div
              v-for="(skill, index) in localSkills"
              :key="skill.id || ('new-' + index)"
              class="skill-item"
              :class="{ 'active-item': currentIndex === index }"
              @click="selectSkill(index)"
            >
              <el-checkbox
                :value="skill.enabled"
                @click.native.stop
                @change="(val) => toggleEnabled(index, val)"
              />
              <div class="skill-meta">
                <span class="skill-name">{{ skill.skillName || $t('skillDialog.unnamed') }}</span>
                <span class="skill-desc">{{ skill.description || '' }}</span>
              </div>
              <div class="skill-actions">
                <el-button type="text" size="mini" @click.stop="editSkill(index)">
                  {{ $t('skillDialog.edit') }}
                </el-button>
                <el-button type="text" size="mini" class="del-btn" @click.stop="removeSkill(index)">
                  {{ $t('skillDialog.delete') }}
                </el-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-tip">{{ $t('skillDialog.noSkills') }}</div>
        </div>
      </div>

      <!-- 右侧：编辑表单 -->
      <div class="skill-column skill-form-column" v-if="editing">
        <div class="column-header">
          <h4 class="column-title">
            {{ editingIndex === -1 ? $t('skillDialog.add') : $t('skillDialog.edit') }}
          </h4>
        </div>
        <div class="skill-form">
          <el-form label-width="90px" label-position="left">
            <el-form-item :label="$t('skillDialog.skillName')">
              <el-input v-model="form.skillName" :placeholder="$t('skillDialog.skillNameRequired')" />
            </el-form-item>
            <el-form-item :label="$t('skillDialog.description')">
              <el-input v-model="form.description" type="textarea" :rows="2" resize="none" />
            </el-form-item>
            <el-form-item :label="$t('skillDialog.content')">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="8"
                resize="none"
                :placeholder="$t('skillDialog.contentPlaceholder')"
              />
            </el-form-item>
            <el-form-item :label="$t('skillDialog.functions')">
              <el-input
                v-model="functionsText"
                type="textarea"
                :rows="3"
                resize="none"
                :placeholder="$t('skillDialog.functionsHint')"
              />
            </el-form-item>
            <el-form-item :label="$t('skillDialog.files')">
              <el-input
                v-model="filesText"
                type="textarea"
                :rows="4"
                resize="none"
                :placeholder="$t('skillDialog.filesHint')"
              />
            </el-form-item>
            <el-form-item :label="$t('skillDialog.enabled')">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-form>
          <div class="form-footer">
            <el-button @click="cancelEdit">{{ $t('skillDialog.cancel') }}</el-button>
            <el-button type="primary" @click="confirmEdit">{{ $t('skillDialog.save') }}</el-button>
          </div>
        </div>
      </div>
      <div class="skill-column skill-form-column empty-form" v-else>
        <div class="empty-tip">{{ $t('skillDialog.selectOrAdd') }}</div>
      </div>
    </div>

    <div class="drawer-footer">
      <el-button @click="closeDialog">{{ $t('skillDialog.cancel') }}</el-button>
      <el-button type="primary" @click="saveSelection">{{ $t('skillDialog.saveConfig') }}</el-button>
    </div>
  </el-drawer>
</template>

<script>
import i18n from '@/i18n';

export default {
  i18n,
  props: {
    value: Boolean,
    skills: {
      type: Array,
      default: () => []
    },
    agentId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      dialogVisible: this.value,
      localSkills: [],
      editing: false,
      editingIndex: -1,
      currentIndex: -1,
      form: this.emptyForm(),
      functionsText: '',
      filesText: '{}'
    };
  },
  watch: {
    value(v) {
      this.dialogVisible = v;
      if (v) {
        // 进入对话框时，深拷贝传入的技能列表
        this.localSkills = (this.skills || []).map((s) => ({
          id: s.id || null,
          skillName: s.skillName || '',
          description: s.description || '',
          content: s.content || '',
          functions: Array.isArray(s.functions) ? [...s.functions] : (s.functions || []),
          files: s.files && typeof s.files === 'object' ? { ...s.files } : {},
          enabled: s.enabled === undefined ? true : !!s.enabled,
          sort: typeof s.sort === 'number' ? s.sort : 0
        }));
        this.editing = false;
        this.editingIndex = -1;
        this.currentIndex = -1;
      }
    },
    dialogVisible(newVal) {
      this.$emit('input', newVal);
    }
  },
  methods: {
    emptyForm() {
      return {
        id: null,
        skillName: '',
        description: '',
        content: '',
        functions: [],
        files: {},
        enabled: true,
        sort: 0
      };
    },
    addSkill() {
      this.editingIndex = -1;
      this.form = this.emptyForm();
      this.functionsText = '';
      this.filesText = '{}';
      this.editing = true;
    },
    editSkill(index) {
      const skill = this.localSkills[index];
      this.editingIndex = index;
      this.currentIndex = index;
      this.form = {
        id: skill.id || null,
        skillName: skill.skillName || '',
        description: skill.description || '',
        content: skill.content || '',
        functions: [],
        files: {},
        enabled: skill.enabled === undefined ? true : !!skill.enabled,
        sort: typeof skill.sort === 'number' ? skill.sort : 0
      };
      this.functionsText = Array.isArray(skill.functions) ? skill.functions.join('\n') : '';
      this.filesText = this.stringifyJson(skill.files);
      this.editing = true;
    },
    selectSkill(index) {
      this.currentIndex = index;
    },
    toggleEnabled(index, val) {
      this.localSkills[index].enabled = !!val;
    },
    removeSkill(index) {
      this.$confirm(this.$t('skillDialog.deleteConfirm'), this.$t('skillDialog.tip'), {
        confirmButtonText: this.$t('skillDialog.delete'),
        cancelButtonText: this.$t('skillDialog.cancel'),
        type: 'warning'
      }).then(() => {
        this.localSkills.splice(index, 1);
        if (this.editingIndex === index) {
          this.editing = false;
          this.editingIndex = -1;
        } else if (this.editingIndex > index) {
          this.editingIndex -= 1;
        }
        if (this.currentIndex === index) {
          this.currentIndex = -1;
        }
      }).catch(() => {});
    },
    cancelEdit() {
      this.editing = false;
      this.editingIndex = -1;
    },
    stringifyJson(obj) {
      try {
        return JSON.stringify(obj || {}, null, 2);
      } catch (e) {
        return '{}';
      }
    },
    confirmEdit() {
      if (!this.form.skillName || !this.form.skillName.trim()) {
        this.$message.warning(this.$t('skillDialog.skillNameRequired'));
        return;
      }
      let files = {};
      if (this.filesText && this.filesText.trim()) {
        try {
          const parsed = JSON.parse(this.filesText);
          files = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
        } catch (e) {
          this.$message.error(this.$t('skillDialog.jsonError'));
          return;
        }
      }
      const functions = (this.functionsText || '')
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);
      const skill = {
        id: this.form.id || null,
        skillName: this.form.skillName.trim(),
        description: this.form.description || '',
        content: this.form.content || '',
        functions,
        files,
        enabled: !!this.form.enabled,
        sort: typeof this.form.sort === 'number' ? this.form.sort : 0
      };
      if (this.editingIndex === -1) {
        skill.sort = this.localSkills.length;
        this.localSkills.push(skill);
      } else {
        skill.sort = this.localSkills[this.editingIndex].sort || this.editingIndex;
        this.$set(this.localSkills, this.editingIndex, skill);
      }
      this.editing = false;
      this.editingIndex = -1;
    },
    closeDialog() {
      this.editing = false;
      this.editingIndex = -1;
      this.dialogVisible = false;
      this.$emit('input', false);
      this.$emit('dialog-closed', false);
    },
    saveSelection() {
      const payload = this.localSkills.map((s, index) => ({
        id: s.id || null,
        skillName: s.skillName,
        description: s.description,
        content: s.content,
        functions: Array.isArray(s.functions) ? s.functions : [],
        files: s.files && typeof s.files === 'object' ? s.files : {},
        enabled: s.enabled === undefined ? true : !!s.enabled,
        sort: index
      }));
      this.$emit('update-skills', payload);
      this.dialogVisible = false;
      this.$emit('input', false);
      this.$emit('dialog-closed', true);
    }
  }
};
</script>

<style lang="scss" scoped>
.skill-manager {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 12px;
  height: calc(70vh);
}

.custom-header {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #EBEEF5;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .bold-title {
    font-size: 18px;
    font-weight: bold;
    margin: 0;
  }

  .count-tip {
    font-size: 13px;
    color: #909399;
  }
}

.skill-column {
  position: relative;
  display: flex;
  flex-direction: column;
  width: auto;
  height: 100%;
  padding: 10px;
  border-right: 1px solid #EBEEF5;
  scrollbar-width: none;
  overflow-x: hidden;
  box-sizing: border-box;

  &.skill-form-column {
    flex: 1;
    border-right: none;
    overflow-y: auto;
  }
}

.skill-column::-webkit-scrollbar {
  display: none;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.column-title {
  text-align: left;
  font-size: 15px;
  font-weight: 600;
  margin: 0;
}

.skill-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skill-item {
  padding: 8px 12px;
  margin: 4px 0;
  width: 320px;
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #EBEEF5;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f5f7fa;
  }

  &.active-item {
    background-color: #ecf0ff;
    border-color: #5778ff;
  }
}

.skill-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;

  .skill-name {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
  }

  .skill-desc {
    font-size: 12px;
    color: #909399;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.skill-actions {
  display: flex;
  gap: 4px;

  .del-btn {
    color: #f56c6c;
  }
}

.skill-form {
  padding: 8px 16px;

  .form-footer {
    text-align: right;
    margin-top: 8px;
  }
}

.empty-form {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-tip {
  padding: 20px;
  color: #909399;
  text-align: center;
  width: 100%;
}

.drawer-footer {
  position: absolute;
  bottom: 0;
  z-index: 2;
  width: 100%;
  border-top: 1px solid #e8e8e8;
  padding: 10px 16px;
  text-align: center;
  background: #fff;
}

.custom-close-btn {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  width: 35px;
  height: 35px;
  border-radius: 50%;
  border: 2px solid #cfcfcf;
  background: none;
  font-size: 30px;
  font-weight: lighter;
  color: #cfcfcf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  padding: 0;
  outline: none;
  transition: all 0.3s;

  &:hover {
    color: #409EFF;
    border-color: #409EFF;
  }
}
</style>
