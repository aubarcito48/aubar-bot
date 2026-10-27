from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import test_app
from pc.aubar_control.config import DEFAULT_MODEL, DEFAULT_TIMEOUT, load_groq_config

FAKE_KEY='synthetic-config-test-token'


class GroqConfigurationTests(unittest.TestCase):
    def test_missing_key_is_optional_and_explains_how_to_configure_it(self):
        with tempfile.TemporaryDirectory() as temp:
            state=load_groq_config(Path(temp)/'.env',environ={})
        self.assertFalse(state.ready)
        self.assertIsNone(state.config)
        self.assertIn('Falta GROQ_API_KEY',state.message)

    def test_file_supports_bom_quotes_and_custom_model_and_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env'
            path.write_text(f'GROQ_API_KEY="{FAKE_KEY}"\nGROQ_MODEL=another/model\nGROQ_TIMEOUT_SECONDS=12.5\n',encoding='utf-8-sig')
            state=load_groq_config(path,environ={})
        self.assertTrue(state.ready)
        self.assertEqual(state.config.api_key,FAKE_KEY)
        self.assertEqual(state.config.model,'another/model')
        self.assertEqual(state.config.timeout_seconds,12.5)

    def test_environment_has_priority_without_mutating_environment_or_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env'
            content=f'GROQ_API_KEY={FAKE_KEY}\nGROQ_TIMEOUT_SECONDS=10\n'
            path.write_text(content,encoding='utf-8')
            with patch.dict(os.environ,{'GROQ_API_KEY':'synthetic-environment-token','GROQ_MODEL':'environment/model'},clear=True):
                before=dict(os.environ)
                state=load_groq_config(path)
                self.assertEqual(dict(os.environ),before)
            self.assertEqual(path.read_text(encoding='utf-8'),content)
        self.assertEqual(state.config.api_key,'synthetic-environment-token')
        self.assertEqual(state.config.model,'environment/model')
        self.assertEqual(state.config.timeout_seconds,10)

    def test_default_settings_and_explicit_blank_environment_override(self):
        state=load_groq_config(None,{'GROQ_API_KEY':FAKE_KEY})
        self.assertEqual(state.config.model,DEFAULT_MODEL)
        self.assertEqual(state.config.timeout_seconds,DEFAULT_TIMEOUT)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env'
            path.write_text(f'GROQ_API_KEY={FAKE_KEY}',encoding='utf-8')
            self.assertFalse(load_groq_config(path,{'GROQ_API_KEY':''}).ready)

    def test_invalid_settings_fail_with_fixed_messages_without_echoing_values(self):
        invalid={
            'GROQ_API_KEY':['two words','line\nbreak','${OTHER_KEY}','tu_api_key'],
            'GROQ_MODEL':['','bad model','value\nother'],
            'GROQ_TIMEOUT_SECONDS':['','NaN','inf','0','121',FAKE_KEY],
        }
        for name,values in invalid.items():
            for value in values:
                with self.subTest(name=name,value=value):
                    state=load_groq_config(None,{'GROQ_API_KEY':FAKE_KEY,name:value})
                    self.assertFalse(state.ready)
                    self.assertIn(name,state.message)
                    self.assertNotIn(FAKE_KEY,str(state))

    def test_config_repr_messages_and_parser_warnings_never_include_key(self):
        state=load_groq_config(None,{'GROQ_API_KEY':FAKE_KEY})
        self.assertNotIn(FAKE_KEY,repr(state))
        self.assertNotIn(FAKE_KEY,repr(state.config))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env'
            path.write_text(f'GROQ_API_KEY="{FAKE_KEY}\n',encoding='utf-8')
            output=io.StringIO()
            with redirect_stderr(output):
                rejected=load_groq_config(path,environ={})
            self.assertFalse(rejected.ready)
            self.assertNotIn(FAKE_KEY,output.getvalue()+repr(rejected))

    def test_values_are_not_interpolated_from_other_environment_secrets(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env'
            path.write_text('GROQ_API_KEY=${OTHER_KEY}',encoding='utf-8')
            with patch.dict(os.environ,{'OTHER_KEY':FAKE_KEY}):
                state=load_groq_config(path,environ={})
            self.assertFalse(state.ready)
            self.assertNotIn(FAKE_KEY,repr(state))

    def test_read_error_does_not_expose_exception_details(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'.env';path.touch()
            with patch('pc.aubar_control.config.dotenv_values',side_effect=OSError(FAKE_KEY)):
                state=load_groq_config(path,environ={})
        self.assertFalse(state.ready)
        self.assertIn('No se pudo leer',state.message)
        self.assertNotIn(FAKE_KEY,repr(state))


class ConfigurationPanelTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump

    def test_reload_detects_configuration_without_displaying_credentials(self):
        self.assertIsNone(self.app.groq_config)
        self.assertIn('Falta GROQ_API_KEY',self.app.groq_config_message.get())
        self.app.config_loader=lambda:load_groq_config(None,{'GROQ_API_KEY':FAKE_KEY})
        self.app.reload_groq_configuration()
        self.assertEqual(self.app.groq_config.api_key,FAKE_KEY)
        self.assertIn('Configuración local lista',self.app.groq_config_message.get())
        self.assertNotIn(FAKE_KEY,self.app.groq_config_message.get())
        self.assertNotIn(FAKE_KEY,self.app.activity.get('1.0','end'))
        self.app.config_loader=lambda:load_groq_config(None,environ={})
        self.app.reload_groq_configuration()
        self.assertIsNone(self.app.groq_config)

    def test_invalid_configuration_does_not_block_device_or_local_voice(self):
        self.app.config_loader=lambda:load_groq_config(None,{'GROQ_API_KEY':FAKE_KEY,'GROQ_TIMEOUT_SECONDS':'NaN'})
        self.app.reload_groq_configuration()
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.app.test_speech()
        self.pump(lambda:len(self.app.speech.calls)==1)
        self.assertTrue(self.app.connected)
        self.assertIsNone(self.app.groq_config)
