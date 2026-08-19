<template>
  <el-drawer :visible.sync="dialogVisible" direction="rtl" size="80%" :wrapperClosable="false" :withHeader="false">
    <div class="custom-header">
      <div class="header-left">
        <h3 class="bold-title">{{ $t('mcpServerDialog.title') }}</h3>
        <span class="count-tip">{{ $t('mcpServerDialog.serversCount', { count: localServers.length }) }}</span>
      </div>
      <button class="custom-close-btn" @click="closeDialog">×</button>
    </div>

    <div class="mcp-manager">
      <!-- 左侧：服务列表 -->
      <div class="mcp-column">
        <div class="column-header">
          <h4 class="column-title">{{ $t('mcpServerDialog.serverList') }}</h4>
          <el-button type="primary" size="small" @click="addServer">
            {{ $t('mcpServerDialog.add') }}
          </el-button>
        </div>
        <div class="mcp-list">
          <div v-if="localServers.length">
            <div
              v-for="(server, index) in localServers"
              :key="server.id || ('new-' + index)"
              class="mcp-item"
              :class="{ 'active-item': currentIndex === index }"
              @click="selectServer(index)"
            >
              <el-checkbox
                :value="server.enabled"
                @click.native.stop
                @change="(val) => toggleEnabled(index, val)"
              />
              <div class="mcp-meta">
                <span class="server-name">{{ server.serverName || $t('mcpServerDialog.unnamed') }}</span>
                <span class="server-transport">{{ server.transport || 'stdio' }}</span>
              </div>
              <div class="mcp-actions">
                <el-button type="text" size="mini" @click.stop="editServer(index)">
                  {{ $t('mcpServerDialog.edit') }}
                </el-button>
                <el-button type="text" size="mini" class="del-btn" @click.stop="removeServer(index)">
                  {{ $t('mcpServerDialog.delete') }}
                </el-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-tip">{{ $t('mcpServerDialog.noServers') }}</div>
        </div>
      </div>

      <!-- 右侧：编辑表单 -->
      <div class="mcp-column mcp-form-column" v-if="editing">
        <div class="column-header">
          <h4 class="column-title">
            {{ editingIndex === -1 ? $t('mcpServerDialog.add') : $t('mcpServerDialog.edit') }}
          </h4>
        </div>
        <div class="mcp-form">
          <el-form label-width="90px" label-position="left">
            <el-form-item :label="$t('mcpServerDialog.serverName')">
              <el-input v-model="form.serverName" :placeholder="$t('mcpServerDialog.serverNameRequired')" />
            </el-form-item>
            <el-form-item :label="$t('mcpServerDialog.transport')">
              <el-select v-model="form.transport" class="full-width">
                <el-option label="stdio" value="stdio" />
                <el-option label="sse" value="sse" />
                <el-option label="streamable-http" value="streamable-http" />
              </el-select>
            </el-form-item>

            <template v-if="form.transport === 'stdio'">
              <el-form-item :label="$t('mcpServerDialog.command')">
                <el-input v-model="form.command" :placeholder="$t('mcpServerDialog.commandPlaceholder')" />
              </el-form-item>
              <el-form-item :label="$t('mcpServerDialog.args')">
                <el-input
                  v-model="argsText"
                  type="textarea"
                  :rows="3"
                  resize="none"
                  :placeholder="$t('mcpServerDialog.argsHint')"
                />
              </el-form-item>
            </template>
            <template v-else>
              <el-form-item :label="$t('mcpServerDialog.url')">
                <el-input v-model="form.url" :placeholder="$t('mcpServerDialog.urlPlaceholder')" />
              </el-form-item>
            </template>

            <el-form-item :label="$t('mcpServerDialog.env')">
              <el-input
                v-model="envText"
                type="textarea"
                :rows="3"
                resize="none"
                :placeholder="$t('mcpServerDialog.envHint')"
              />
            </el-form-item>
            <el-form-item :label="$t('mcpServerDialog.headers')">
              <el-input
                v-model="headersText"
                type="textarea"
                :rows="3"
                resize="none"
                :placeholder="$t('mcpServerDialog.headersHint')"
              />
            </el-form-item>
            <el-form-item :label="$t('mcpServerDialog.enabled')">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-form>
          <div class="form-footer">
            <el-button @click="cancelEdit">{{ $t('mcpServerDialog.cancel') }}</el-button>
            <el-button type="primary" @click="confirmEdit">{{ $t('mcpServerDialog.save') }}</el-button>
          </div>
        </div>
      </div>
      <div class="mcp-column mcp-form-column empty-form" v-else>
        <div class="empty-tip">{{ $t('mcpServerDialog.selectOrAdd') }}</div>
      </div>
    </div>

    <div class="drawer-footer">
      <el-button @click="closeDialog">{{ $t('mcpServerDialog.cancel') }}</el-button>
      <el-button type="primary" @click="saveSelection">{{ $t('mcpServerDialog.saveConfig') }}</el-button>
    </div>
  </el-drawer>
</template>

<script>
import i18n from '@/i18n';

export default {
  i18n,
  props: {
    value: Boolean,
    mcpServers: {
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
      localServers: [],
      editing: false,
      editingIndex: -1,
      currentIndex: -1,
      form: this.emptyForm(),
      argsText: '',
      envText: '{}',
      headersText: '{}'
    };
  },
  watch: {
    value(v) {
      this.dialogVisible = v;
      if (v) {
        this.localServers = (this.mcpServers || []).map((s) => ({
          id: s.id || null,
          serverName: s.serverName || '',
          transport: s.transport || 'stdio',
          command: s.command || '',
          args: Array.isArray(s.args) ? [...s.args] : (s.args || []),
          url: s.url || '',
          env: s.env && typeof s.env === 'object' ? { ...s.env } : {},
          headers: s.headers && typeof s.headers === 'object' ? { ...s.headers } : {},
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
        serverName: '',
        transport: 'stdio',
        command: '',
        args: [],
        url: '',
        env: {},
        headers: {},
        enabled: true,
        sort: 0
      };
    },
    addServer() {
      this.editingIndex = -1;
      this.form = this.emptyForm();
      this.argsText = '';
      this.envText = '{}';
      this.headersText = '{}';
      this.editing = true;
    },
    editServer(index) {
      const server = this.localServers[index];
      this.editingIndex = index;
      this.currentIndex = index;
      this.form = {
        id: server.id || null,
        serverName: server.serverName || '',
        transport: server.transport || 'stdio',
        command: server.command || '',
        args: [],
        url: server.url || '',
        env: {},
        headers: {},
        enabled: server.enabled === undefined ? true : !!server.enabled,
        sort: typeof server.sort === 'number' ? server.sort : 0
      };
      this.argsText = Array.isArray(server.args) ? server.args.join('\n') : '';
      this.envText = this.stringifyJson(server.env);
      this.headersText = this.stringifyJson(server.headers);
      this.editing = true;
    },
    selectServer(index) {
      this.currentIndex = index;
    },
    toggleEnabled(index, val) {
      this.localServers[index].enabled = !!val;
    },
    removeServer(index) {
      this.$confirm(this.$t('mcpServerDialog.deleteConfirm'), this.$t('mcpServerDialog.tip'), {
        confirmButtonText: this.$t('mcpServerDialog.delete'),
        cancelButtonText: this.$t('mcpServerDialog.cancel'),
        type: 'warning'
      }).then(() => {
        this.localServers.splice(index, 1);
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
    parseJsonField(text, fallback) {
      if (!text || !text.trim()) {
        return fallback;
      }
      try {
        const parsed = JSON.parse(text);
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : fallback;
      } catch (e) {
        this.$message.error(this.$t('mcpServerDialog.jsonError'));
        return null;
      }
    },
    confirmEdit() {
      if (!this.form.serverName || !this.form.serverName.trim()) {
        this.$message.warning(this.$t('mcpServerDialog.serverNameRequired'));
        return;
      }
      const env = this.parseJsonField(this.envText, {});
      if (env === null) return;
      const headers = this.parseJsonField(this.headersText, {});
      if (headers === null) return;

      const args = (this.argsText || '')
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

      const server = {
        id: this.form.id || null,
        serverName: this.form.serverName.trim(),
        transport: this.form.transport || 'stdio',
        command: this.form.command || '',
        args,
        url: this.form.url || '',
        env,
        headers,
        enabled: !!this.form.enabled,
        sort: typeof this.form.sort === 'number' ? this.form.sort : 0
      };
      if (this.editingIndex === -1) {
        server.sort = this.localServers.length;
        this.localServers.push(server);
      } else {
        server.sort = this.localServers[this.editingIndex].sort || this.editingIndex;
        this.$set(this.localServers, this.editingIndex, server);
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
      const payload = this.localServers.map((s, index) => ({
        id: s.id || null,
        serverName: s.serverName,
        transport: s.transport || 'stdio',
        command: s.command,
        args: Array.isArray(s.args) ? s.args : [],
        url: s.url,
        env: s.env && typeof s.env === 'object' ? s.env : {},
        headers: s.headers && typeof s.headers === 'object' ? s.headers : {},
        enabled: s.enabled === undefined ? true : !!s.enabled,
        sort: index
      }));
      this.$emit('update-mcp-servers', payload);
      this.dialogVisible = false;
      this.$emit('input', false);
      this.$emit('dialog-closed', true);
    }
  }
};
</script>

<style lang="scss" scoped>
.mcp-manager {
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

.mcp-column {
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

  &.mcp-form-column {
    flex: 1;
    border-right: none;
    overflow-y: auto;
  }
}

.mcp-column::-webkit-scrollbar {
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

.mcp-list {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mcp-item {
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

.mcp-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;

  .server-name {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
  }

  .server-transport {
    font-size: 12px;
    color: #909399;
  }
}

.mcp-actions {
  display: flex;
  gap: 4px;

  .del-btn {
    color: #f56c6c;
  }
}

.mcp-form {
  padding: 8px 16px;

  .full-width {
    width: 100%;
  }

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
