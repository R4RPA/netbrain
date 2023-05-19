



# Restrained Type Aliases
AuthType = Literal['BASIC', 'TOKEN']
RequestType = Literal['GET', 'POST', 'PUT']


class WsgwConfig(BaseModel):
    api_url: str
    api_un: str
    api_pw: str
    auth_type: AuthType = 'BASIC'
    debug: Optional[bool] = False

class Wsgw:
    """
        Ojbect to represent the Web Services Gateway API

        DEV: During development, some output is recorded in local files. This
        will be turned off in PROD.
        """

    def __init__(self, wsgw_config: WsgwConfig):
        # set configuration
        self.config = wsgw_config
        # set authentication
        # TODO:// add token authentication if needed
        if self.config.auth_type == 'BASIC':
            self.auth = HTTPBasicAuth(username=self.config.api_un, password=self.config.api_pw)
        self.headers = {'accept': 'application/json', 'content-type': 'application/json'}
        self.messages: list[Message] = []

    def retrieve_messages(self) -> list[Message]:
        messages = self.messages
        # we want to clear out after we grab them
        # we don't want messages double processed
        self.messages = []
        return messages

    def api_action(self, action: RequestType, url: str, data: Optional[types.PostData] = None, params = None, debug_filename: Optional[str] = None, cid: Cid = get_cid(),) -> Response:
        """
        Direct HTTP Request of the WSGW REST API.

        This method is effectively a wrapper around requests.request()
        """
        logger.info(f'{cid} api_action request being made: action {action} url {url} debug_filename {debug_filename}')
        logger.debug(f'{cid} headers={self.headers} data={data}')
        # data must be json encoded string
        if action == 'GET':
            response: Response = request(method=action, url=url, params=params, headers=self.headers, auth=self.auth)
            return response
        else:
            if data:
                data = json.dumps(data)
            response: Response = request(method=action, url=url, data=data, headers=self.headers, auth=self.auth)

            # if self.config.debug:
            #     # make sure we have the directory available
            #     if not os.path.exists('debug_output'):
            #         try:
            #             os.mkdir('debug_output')
            #         except:
            #             logger.error(f'Unable to create the local directory debug_output', exc_info=True)
            #     # confirm we now have the path, if so then dump output
            #     if os.path.exists('debug_output'):
            #         if response.ok:
            #             with open(f'debug_output\\{debug_filename}_{datetime.now()}.json', 'a') as output:
            #                 json.dump(response.json(), output)
            #             logger.info(f'{cid} DEBUG enabled created output file {debug_filename}.json')
            #         else: # fail message will be in xml
            #             with open(f'debug_output\\{debug_filename}_ERROR.xml', 'a') as output:
            #                 output.write(response.text)
            #             logger.info(f'{cid} DEBUG enabled created output file {debug_filename}_ERROR.xml')

            logger.info(f'{cid} api_action response status_code {response.status_code}')
            if not response.ok:
                raise exceptions.ApiActionError(
                    f'{action} {url} received status_code {response.status_code} {response.text}')
            return response


    # Get Device Data
    def device_data(self, cid: Cid = get_cid()) -> types.DeviceDataResponse:
        url = f'{self.config.api_url}/CMDB/Devices/DeviceRawData?IP=10.139.252.208&dataType=2&cmd=show interface&token=ae547ee8-1da2-4271-8b0a-ad64edae84b4'
