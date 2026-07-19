# 学生心理关怀随访与报表系统

一个面向高校辅导员、心理老师和系统管理员的校内工作系统。项目使用 Vue 3 + FastAPI + PostgreSQL，重点解决学生关怀工作中常见的漏访、记录分散、人员交接困难、转介无闭环和月底统计耗时等问题。

本系统用于关怀工作协同、过程留痕和统计分析，不进行自动心理诊断，也不能替代学校的线下应急处置制度。

## 已实现的核心能力

- 学生档案：基础信息、所属机构、班级、辅导员、紧急联系人、在校状态。
- CSV 批量导入导出：支持中文或英文表头、更新已有学生、逐行错误反馈。
- 关怀个案：发现来源、问题标签、摘要、负责人、保密级别、三级风险和状态流转。
- 单学生单在管个案：数据库和业务层同时阻止重复建立未结案个案。
- 随访任务：计划时间、方式、目的、待办、今日到期和超期提醒。
- 随访记录：改善/稳定/恶化/未联系成功、处理措施、风险调整、自动生成下次任务。
- 风险留痕：记录每次风险等级变化、原因、操作人和时间。
- 心理中心转介：申请、接收、处理、完成/退回以及专业意见，状态由流程维护，不能手工绕过。
- 结案：填写原因、自动取消未完成任务；红色风险个案只能由心理老师结案。
- 工作台：在管个案、红色风险、今日任务、超期任务、本月随访和待处理转介。
- 统计报表：当前在管、期间新增/结案、随访次数、超期数、按时率及风险、状态、问题、机构分布。
- 权限控制：管理员、辅导员和心理老师三类角色；辅导员按机构和负责关系查看数据。
- 受限个案：系统管理员不能打开受限个案详情，受限内容访问会记录审计日志。
- 审计日志：登录、数据导入导出、敏感档案查看、建档、随访、转介、风险调整和结案均可追踪。
- 运维能力：Alembic 数据库迁移、Docker Compose 部署、健康检查、备份恢复脚本和 GitHub Actions CI。

## 角色与数据权限

| 角色 | 主要职责 | 数据范围 |
|---|---|---|
| 系统管理员 | 维护机构、账号、学生基础数据，查看汇总报表和审计日志 | 可管理全局基础数据；不能打开受限个案详情 |
| 辅导员 | 建立个案、安排和完成随访、调整风险、发起转介、结案 | 所属机构学生；可操作自己负责或担任负责人的个案 |
| 心理老师 | 接收转介、填写专业意见、处理全局个案、红色个案结案 | 全校关怀个案和分配给自己的转介 |

为避免责任断档，仍负责在校学生或未结案个案的账号不能直接停用、换机构或改换角色，必须先完成转派。

## 业务闭环

```text
发现需要关注的学生
        ↓
建立关怀个案并确定风险等级
        ↓
创建首次随访任务
        ↓
完成随访并记录状态与措施
        ↓
生成下次任务 / 调整风险 / 发起转介
        ↓
持续观察或心理老师专业处理
        ↓
状态稳定后填写原因并结案
```

个案状态的主要规则：

```text
跟进中 ↔ 稳定观察
跟进中/稳定观察 → 已转介（只能由转介申请触发）
已转介 → 稳定观察（转介完成）
已转介 → 跟进中（转介退回）
任意未结案状态 → 已结案（使用结案操作）
```

## 技术结构

```text
浏览器
  ↓
Nginx（Vue 静态文件、API 反向代理）
  ↓ /api
FastAPI
  ├── SQLAlchemy 2
  ├── Alembic
  ├── JWT + PBKDF2 密码哈希
  └── PostgreSQL
```

项目目录：

```text
.
├── backend/                 FastAPI 后端、迁移和测试
│   ├── app/
│   │   ├── routers/         API 路由
│   │   ├── services/        个案与报表业务逻辑
│   │   ├── models.py        数据模型
│   │   ├── schemas.py       请求与响应模型
│   │   └── permissions.py   数据权限
│   ├── alembic/             数据库迁移
│   └── tests/               后端回归测试
├── frontend/                Vue 3 前端
│   └── src/
│       ├── views/           业务页面
│       ├── components/      通用组件
│       ├── stores/          登录状态
│       └── api/             API 请求封装
├── scripts/                 检查、备份、恢复和密钥脚本
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Linux 上使用 Docker Compose 部署

### 1. 环境要求

- Linux 服务器，推荐 Ubuntu 22.04/24.04 或 Debian 12。
- Docker Engine 和 Docker Compose v2。
- 建议至少 2 GB 内存和 10 GB 可用磁盘。
- 正式环境必须配置 HTTPS，并限制服务器和备份文件访问权限。

### 2. 创建生产配置

```bash
cp .env.example .env
./scripts/generate-secret.sh
```

编辑 `.env`，至少修改以下三项：

```dotenv
SECRET_KEY=上一步生成的随机字符串
INITIAL_ADMIN_PASSWORD=一个新的强密码
POSTGRES_PASSWORD=一个新的数据库密码
DATABASE_URL=postgresql+psycopg://student_care:与上面相同的数据库密码@db:5432/student_care
```

`ENVIRONMENT=production` 时，后端会拒绝使用示例密钥、示例管理员密码或示例数据库密码启动，避免误把不安全配置投入使用。

数据库密码用于 URL 时建议只使用字母、数字、下划线和连字符；包含 `@`、`:`、`/` 等字符时需要进行 URL 编码。

### 3. 启动

```bash
make up
# 或
docker compose up -d --build
```

默认地址：

- 系统页面：`http://服务器地址:8080`
- API 文档：`http://服务器地址:8080/api/docs`
- 健康检查：`http://服务器地址:8080/health`

端口可在 `.env` 中添加 `WEB_PORT=其他端口` 修改。

查看运行状态和日志：

```bash
docker compose ps
make logs
```

停止服务：

```bash
make down
```

### 4. 首次登录后的初始化顺序

1. 使用 `.env` 中的 `INITIAL_ADMIN_USERNAME` 和 `INITIAL_ADMIN_PASSWORD` 登录。
2. 立即在右上角修改管理员密码。
3. 在“组织机构”中创建学院或业务单位。
4. 在“用户管理”中创建辅导员和心理老师账号。
5. 在“学生档案”中新建学生，或下载模板后批量导入 CSV。
6. 进入某个学生档案，建立关怀个案并安排首次随访。

系统不会自动写入演示学生或虚构心理记录，避免测试数据混入正式库。

## 学生 CSV 导入格式

“学生档案”页面可直接下载模板。文件必须使用 UTF-8 编码，最大 5 MB。

支持的中文表头：

```csv
学号,姓名,性别,机构编码,专业,年级,班级,手机号,紧急联系人,紧急联系电话,辅导员账号
20260001,张三,男,CS,软件工程,2026,软件2601,13800000000,家长,13900000000,counselor1
```

也支持对应英文表头：

```text
student_no,name,gender,organization_code,major,grade,class_name,phone,
emergency_contact_name,emergency_contact_phone,counselor_username
```

其中学号、姓名和机构编码必填。辅导员导入时，学生会自动归到当前辅导员名下，并且只能导入本机构学生。

## 数据备份与恢复

心理关怀数据属于敏感数据。备份目录默认权限为 `700`，备份文件权限为 `600`，但仍应将备份存放在加密磁盘或受控的对象存储中。

创建 PostgreSQL 自定义格式备份：

```bash
make backup
# 或指定文件
./scripts/backup.sh /安全目录/student-care.dump
```

恢复会覆盖当前数据库，必须显式确认：

```bash
make restore FILE=backups/student-care-20260719-120000.dump
# 或
RESTORE_CONFIRM=YES ./scripts/restore.sh backups/student-care-20260719-120000.dump
```

建议至少执行：每日自动备份、异机保存、定期恢复演练、备份保留周期管理和离职人员权限回收。

## 本地开发

### 后端

推荐 Python 3.12。

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ENVIRONMENT=development
export SECRET_KEY=local-development-secret-key-at-least-32-characters
export DATABASE_URL=sqlite:///./student_care.db
export AUTO_CREATE_TABLES=true
export INITIAL_ADMIN_USERNAME=admin
export INITIAL_ADMIN_PASSWORD=Admin123!

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端开发地址为 `http://127.0.0.1:8000`，API 文档为 `http://127.0.0.1:8000/api/docs`。

### 前端

推荐 Node.js 22。

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

## 质量检查

执行全部本地检查：

```bash
./scripts/check.sh
# 或
make check
```

检查内容包括：

- 后端 pytest 业务回归测试。
- Python 源码编译检查。
- Vue TypeScript 类型检查。
- Vite 生产构建。

GitHub Actions 会在推送和 Pull Request 时执行同样的后端与前端检查。

## 生产使用检查清单

正式保存真实学生数据前，应完成以下事项：

- 使用学校域名和 HTTPS，不通过公网明文 HTTP 使用。
- 修改所有默认密码和密钥，不把 `.env` 提交到 Git。
- 限制服务器、数据库、审计日志和备份的访问人员。
- 根据学校制度确定数据保存期限、导出审批和账号回收流程。
- 定期检查超期任务、红色风险个案、未处理转介和长期未登录账号。
- 对数据库和备份执行恢复演练，而不是只确认“备份文件存在”。
- 在学校应急预案中明确红色风险的线下联系人、值班电话和升级路径。
- 不把系统提示作为心理诊断、医疗建议或紧急处置结论。

## 设计边界

为了保持可靠、易维护和可实际落地，当前版本没有引入微服务、消息队列、自动情绪识别、大模型诊断、聊天机器人或手机 App。随访提醒直接由数据库中的计划时间驱动，登录工作台即可看到今日和超期任务；这能覆盖核心工作问题，同时避免不必要的部署复杂度。
