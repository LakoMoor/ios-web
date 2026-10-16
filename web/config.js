export const roles = [
  ['kernel','kernelcache','Ядро / Mach-O или IMG4',true],
  ['dtb','DeviceTree','Дерево устройств / IMG4',true],
  ['trustcache','TrustCache','Кэш доверия / IMG4',true],
  ['disk','System disk','Подготовленный образ RAW / QCOW2',true],
  ['nvram','NVRAM','Банк CHRP NVRAM / RAW',true],
  ['initrd','Ramdisk','Необязательно: загрузочный RAM-диск',false],
  ['seprom','SEP ROM','Необязательно: ROM Secure Enclave',false],
  ['sepfw','SEP firmware','Необязательно: расшифрованная SEP FW',false],
  ['ticket','AP Ticket','Необязательно: AP ticket',false],
];
export function validateConfig(config, files) {
  if (!['t8030','s8000'].includes(config.machine)) throw new Error('Неизвестное устройство');
  const maximum = config.swap ? 4096 : 1792;
  if (!Number.isInteger(config.memory) || config.memory < 512 || config.memory > maximum) throw new Error('Допустимо от 512 до '+maximum+' МБ памяти');
  if (config.swap && config.machine !== 't8030') throw new Error('Подкачка пока поддерживает T8030. Для S8000 отключите её.');
  if (config.swap && ![64,128,256,512].includes(config.swapCache)) throw new Error('Некорректный размер кэша подкачки');
  if (!['raw','qcow2'].includes(config.format)) throw new Error('Неизвестный формат диска');
  const missing = roles.filter(([id,,,required]) => required && !files[id]?.size).map(([,name]) => name);
  if (missing.length) throw new Error('Выберите файлы: ' + missing.join(', '));
  if (Boolean(files.seprom) !== Boolean(files.sepfw)) throw new Error('SEP ROM и SEP firmware нужны вместе');
  if (typeof config.bootargs !== 'string' || config.bootargs.length > 4096 || config.bootargs.includes('\0')) throw new Error('Некорректные аргументы ядра');
  return true;
}
export function bootArguments(config, files) {
  validateConfig(config, files);
  const props = [config.machine, 'trustcache=/input/trustcache'];
  if (files.seprom) props.push('sep-rom=/input/seprom','sep-fw=/input/sepfw');
  if (files.ticket) props.push('ticket=/input/ticket');
  const args = ['-M',props.join(','),'-accel','tcg,thread=single,tb-size=32','-m',String(config.memory),'-smp',files.seprom?'2':'1','-display','browser','-serial','stdio','-monitor','none','-nic','none','-snapshot',
    '-kernel','/input/kernel','-dtb','/input/dtb','-append',config.bootargs,
    '-drive','if=none,id=system,file=/input/disk,format='+config.format,
    '-device','nvme-ns,drive=system,bus=nvme-bus.0,nsid=1',
    '-drive','if=none,id=nvram-store,file=/input/nvram,format=raw',
    '-device','apple-nvram,id=nvram,drive=nvram-store,bus=nvme-bus.0,nsid=2'];
  if (files.initrd) args.push('-initrd','/input/initrd');
  return args;
}
export function probeArguments(paged=false) { return ['-M','virt','-cpu','cortex-a53','-accel','tcg,thread=single,tb-size=32','-m',paged?'4096':'128','-smp','1','-display','browser','-serial','stdio','-monitor','none','-nic','none','-device','loader,file=/probe.bin,addr='+(paged?'0x100080000':'0x40080000')+',cpu-num=0']; }
export function pointerPosition(rect, width, height, x, y) {
  const scale = Math.min(rect.width/width, rect.height/height);
  const left = rect.left + (rect.width-width*scale)/2, top = rect.top + (rect.height-height*scale)/2;
  return {x:Math.round(Math.max(0,Math.min(1,(x-left)/(width*scale)))*32767),y:Math.round(Math.max(0,Math.min(1,(y-top)/(height*scale)))*32767)};
}
