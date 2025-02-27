import datetime
import re
import imggen
import botpy
from botpy import logging
from botpy.message import GroupMessage, C2CMessage
from botpy.robot import Token
from openai import OpenAI
from pyppeteer import launch
import os
_log = logging.get_logger()
BOT_APPID = '111111111'  # 机器人应用ID
BOT_SECRET = 'aaaaaaaaaaaaaaaaaaaaaaaaaa'  # 机器人密钥
API_KEY = "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # deepseek的api key
ini_content = '''你是人机'''


class MyClient(botpy.Client):
	def __init__(self, intents):
		super().__init__(intents=intents)
        #这里的url改成你那边的url
		self.ai = OpenAI(api_key=API_KEY, base_url="https://api.lkeap.cloud.tencent.com/v1")
		self.ai.timeout = 300
		self.temperature = 1.5
		self.messagedic = {}  # 用于存储每个会话的消息历史
		self.browser=None


	async def _bot_login(self, token: Token) -> None:
		await super()._bot_login(token)
		self._connection._max_async = 5

	async def on_ready(self):
		_log.info("正在启动浏览器")
		# 启动浏览器
		self.browser = await launch(headless=True,args=['--no-sandbox', '--disable-setuid-sandbox'])
		_log.info("浏览器启动完毕")
		_log.info(f"robot 「{self.robot.name}」 on_ready!")

	def check_temperature_command(self,text,is_group=True):
		pattern = r'^/温度\s+(\d+(\.\d+)?)$' if not is_group else r'^\s+/温度\s+(\d+(\.\d+)?)$'
		match = re.match(pattern, text)
		if match:
			# 提取数字部分
			number = float(match.group(1))
			# 判断数字是否在 0 到 2 之间
			if 0 <= number <= 2:
				self.temperature = number
				return True
		return False
	def check_clean_mem(self,text,is_group=True):
		pattern = r'^\s+/清除记忆 $' if is_group else r'^/清除记忆 $'
		return re.match(pattern, text)

	async def _process_message(self, message, is_group):
		"""处理消息并生成AI回复"""
		_log.info("收到消息： "+message.content)
		if self.check_temperature_command(message.content,is_group):
			return "温度设置完毕。"
		id = message.group_openid if is_group else message.author.user_openid
		if self.check_clean_mem(message.content,is_group):
			if id in self.messagedic:
				del self.messagedic[id]
			return "记忆已经清除"

		if id not in self.messagedic:
			self.messagedic[id] = [
				{"role": "system", "content": ini_content},
				{"role": "user", "content": message.content},
			]
		else:
			if self.messagedic[id][-1]["role"] != "user":
				self.messagedic[id].append({"role": "user", "content": message.content})

		try:
            
            #根据你的平台这里的参数也要适当修改
			ai_response = self.ai.chat.completions.create(
				model="deepseek-r1",
				messages=self.messagedic[id],
				stream=False,
				temperature=self.temperature,
				)
		except Exception as e:
			# 捕获并打印原始响应内容
			if hasattr(e, 'response'):
				raw_response = e.response.text  # 获取原始响应文本
				_log.exception(f"API原始响应：{raw_response}")
			_log.exception("API请求异常")
			return await self._process_message(message, is_group)

		assistant_content = ai_response.choices[0].message.content
		self.messagedic[id].append({"role": ai_response.choices[0].message.role,"content": assistant_content})
		return r"> "+ai_response.choices[0].message.reasoning_content+"\n\n"+assistant_content
		#return "\n\n"+assistant_content

	async def on_c2c_message_create(self, message: C2CMessage):
		"""处理好友私聊消息"""
		final_content = await self._process_message(message, is_group=False)
		if final_content:
			imgname = "qqbot_"+datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".png"
			imgpath = "你的路径" + imgname
			await imggen.convert_md_to_image(self.browser,final_content, imgpath)
			uploadMedia = await message._api.post_c2c_file(
				openid=message.author.user_openid,
				file_type=1,  # 文件类型要对应上，具体支持的类型见方法说明
				url="你的的url"+imgname  # 文件Url
			)
			_log.info(await message._api.post_c2c_message(
            	openid=message.author.user_openid,
            	msg_type=7,  # 7表示富媒体类型
            	msg_id=message.id,
            	media=uploadMedia
        		)
			)
			os.remove(imgpath)




	async def on_group_at_message_create(self, message: GroupMessage):
		"""处理群聊@消息"""
		final_content = await self._process_message(message, is_group=True)
		if final_content:
			imgname = "qqbot_"+datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ".png"
			imgpath = "你的路径" + imgname
			await imggen.convert_md_to_image(self.browser, final_content, imgpath)
			uploadMedia = await message._api.post_group_file(
				group_openid=message.group_openid,
				file_type=1,  # 文件类型要对应上，具体支持的类型见方法说明
				url="你的的url"+imgname  # 文件Url
			)

			_log.info(await message._api.post_group_message(
				group_openid=message.group_openid,
				msg_type=7, msg_id=message.id,
				media = uploadMedia
			))
			os.remove(imgpath)


if __name__ == "__main__":
	# 通过kwargs，设置需要监听的事件通道
	intents = botpy.Intents(public_messages=True)
	client = MyClient(intents)
	client.timeout = 300
	client.run(appid=BOT_APPID, secret=BOT_SECRET)