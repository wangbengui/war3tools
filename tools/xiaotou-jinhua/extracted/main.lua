local dbg = require 'jass.debug'
-- 每一行输出的数据项数
-- 让输出的文本更紧凑, 防止内容超出屏幕看不到
-- 由于WE里字符串长度过长会导致崩溃, 这个值不宜过大
local ECHO_PER_LINE = 2
setmetatable(_ENV, {__index = getmetatable(require "jass.common").__index})
function echo(str)
    DisplayTimedTextToPlayer(Player(0), 0, 0, 60.00, str)
end
local name_map = {
    ['+loc'] = '点',
    ['+EIP'] = '特效I',
    ['+EIm'] = '特效II',
    ['+tmr'] = '计时器',
    ['item'] = '物品',
    ['+w3u'] = '单位',
    ['+grp'] = '单位组',
    ['+dlb'] = '按钮',
    ['+dlg'] = '对话框',
    ['+w3d'] = '破坏物',
    ['+rev'] = '事件',
    ['alvt'] = '事件',
    ['bevt'] = '事件',
    ['devt'] = '事件',
    ['gevt'] = '事件',
    ['gfvt'] = '事件',
    ['pcvt'] = '事件',
    ['pevt'] = '事件',
    ['psvt'] = '事件',
    ['tmet'] = '事件',
    ['tmvt'] = '事件',
    ['uevt'] = '事件',
    ['+flt'] = 'Filter',
    ['+fgm'] = '可见度修正器',
    ['+frc'] = '玩家组',
    ['ghth'] = '哈希表',
    ['+mdb'] = '多面版',
    ['+ply'] = '玩家',
    ['+rct'] = '矩形区域',
    ['+agr'] = '范围',
    ['+snd'] = '声音',
    ['+tid'] = '计时器窗口',
    ['+trg'] = '触发器',
    ['+tac'] = '触发器动作',
    ['tcnd'] = '触发条件',
}
local saved_map = {}
local sum_saved = 0
function display_jass_object()
    --统计句柄数量
    local sum_count = 0
    local sum_delta = 0
    local count_map = {}
    local delta_map = {}
    print('handlemax = '..dbg.handlemax())
    for h = 0, dbg.handlemax() do
        local def = dbg.handledef(0x100000 + h)
        if def and def.type then 
            local name = name_map[def.type] or '其他对象'
            count_map[name] = (count_map[name] or 0) + 1
            sum_count = sum_count + 1
        end
    end
    -- 计算计数偏移
    if sum_saved > 0 then
        sum_delta = sum_count - sum_saved
        for k,v in pairs(count_map) do
            delta_map[k] = v - (saved_map[k] or 0)
            saved_map[k] = v
        end
    else
        for k,v in pairs(count_map) do
            delta_map[k] = 0
            saved_map[k] = v
        end
    end
    sum_saved = sum_count
    local msg = ''
    local step = 0
    local green = {r = 40, g = 255, b = 10}
    local yellow = {r = 255, g = 220, b = 20}
    local red = {r = 255, g = 30, b = 25}
    echo('--------------------------------')
    echo('|cffffcc00句柄检测:|r'..os.date(' @%H:%M:%S'))
    for k,v in pairs(count_map) do
        v = v or 0
        if v > 0 or delta_map[k] ~= 0 then
            if string.len(msg) > 0 then
                msg = msg..', '
            end
            -- 颜色进度, 数值越接近X越红, 反之则越绿
            local p = math.min(v / 10000, 1)
            local color = {}
            if p < 0.5 then
                p = p / 0.5
                color.r = math.ceil(green.r + (yellow.r - green.r) * p)
                color.g = math.ceil(green.g + (yellow.g - green.g) * p)
                color.b = math.ceil(green.b + (yellow.b - green.b) * p)
            else
                p = p / 0.5 - 1
                color.r = math.ceil(yellow.r + (red.r - yellow.r) * p)
                color.g = math.ceil(yellow.g + (red.g - yellow.g) * p)
                color.b = math.ceil(yellow.b + (red.b - yellow.b) * p)
            end
            local rgb = string.format('%02x%02x%02x', color.r, color.g, color.b)
            msg = msg..string.format('%s:|cff%s%s|r', k, rgb, v)
            -- 展示计数偏移
            if delta_map[k] ~= 0 then
                local prefix = ''
                if delta_map[k] > 0 then
                    prefix = 'ff0000↑'
                else
                    prefix = '00ff00↓'
                end
                msg = msg..string.format('(|cff%s%d|r)', prefix, math.abs(delta_map[k]))
            end
            -- 每隔X个数据, 输出一行
            step = step + 1
            if step >= ECHO_PER_LINE then
                echo(msg)
                step = 0
                msg = ''
            end
        end
    end
    -- 尾部数据(数量不满X, 多出来的)
    if step > 0 then
        echo(msg)
    end
    -- 总计数量
    msg = '统计数量: '..sum_count
    if sum_delta ~= 0 then
        local prefix = ''
        if sum_delta > 0 then
            prefix = 'ff0000↑'
        else
            prefix = '00ff00↓'
        end
        msg = msg..string.format('(|cff%s%d|r)', prefix, math.abs(sum_delta))
    end
    msg = msg..', 底层获取数量:'..dbg.handlecount()
    echo(msg)
    echo('--------------------------------')
end
local trig = CreateTrigger()
TriggerRegisterPlayerEvent(trig, Player(0), EVENT_PLAYER_END_CINEMATIC)
TriggerAddAction(trig, display_jass_object)
