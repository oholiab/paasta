import check_marathon_services_http_frontends
import mock
import contextlib
import subprocess


def test_build_check_http_command():
    port = 666
    expected = '/usr/lib/nagios/plugins/check_http -H localhost -p 666'
    actual = check_marathon_services_http_frontends.build_check_http_command(port)
    assert expected == actual


def test_check_http():
    fake_port = 19343
    fake_command = '/usr/bin/check_sandwich working_girls'
    fake_output = 'vader_nooooooo.jpg'
    fake_process = mock.Mock(returncode=11, communicate=mock.Mock(return_value=(fake_output, '42')))
    expected = (11, fake_output)
    with contextlib.nested(
        mock.patch('check_marathon_services_http_frontends.build_check_http_command',
                   return_value=fake_command),
        mock.patch('subprocess.Popen',
                   return_value=fake_process)
    ) as (
        build_cmd_patch,
        popen_patch,
    ):
        actual = check_marathon_services_http_frontends.check_http(fake_port)
        assert expected == actual
        build_cmd_patch.assert_called_once_with(fake_port)
        popen_patch.assert_called_once_with(fake_command.split(),
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)


def test_send_event():
    fake_service_name = 'fake_service'
    fake_instance_name = 'fake_instance'
    fake_check_name = 'soa_bla'
    fake_status = '42'
    fake_output = 'The http port is not open'
    fake_runbook = 'y/fakerunbook'
    fake_team = 'fake_team'
    fake_tip = 'fake_tip'
    fake_notification_email = 'fake@notify'
    fake_page = False
    fake_alert_after = '42m'
    expected_kwargs = {
        'tip': fake_tip,
        'notification_email': fake_notification_email,
        'page': fake_page,
        'alert_after': fake_alert_after,
        'realert_every': -1,
    }
    with contextlib.nested(
        mock.patch("service_deployment_tools.monitoring_tools.get_team",
                   return_value=fake_team),
        mock.patch("service_deployment_tools.monitoring_tools.get_runbook",
                   return_value=fake_runbook),
        mock.patch("service_deployment_tools.monitoring_tools.get_tip",
                   return_value=fake_tip),
        mock.patch("service_deployment_tools.monitoring_tools.get_notification_email",
                   return_value=fake_notification_email),
        mock.patch("service_deployment_tools.monitoring_tools.get_page",
                   return_value=fake_page),
        mock.patch("service_deployment_tools.monitoring_tools.get_alert_after",
                   return_value=fake_alert_after),
        mock.patch("pysensu_yelp.send_event"),
    ) as (
        monitoring_tools_get_team_patch,
        monitoring_tools_get_runbook_patch,
        monitoring_tools_get_tip_patch,
        monitoring_tools_get_notification_email_patch,
        monitoring_tools_get_page_patch,
        monitoring_tools_get_alert_after_patch,
        pysensu_yelp_send_event_patch,
    ):
        check_marathon_services_http_frontends.send_event(fake_service_name,
                                                          fake_instance_name,
                                                          fake_check_name,
                                                          fake_status,
                                                          fake_output)
        monitoring_tools_get_team_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        monitoring_tools_get_runbook_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        monitoring_tools_get_tip_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        monitoring_tools_get_notification_email_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        monitoring_tools_get_page_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        monitoring_tools_get_alert_after_patch.assert_called_once_with('marathon', fake_service_name, fake_instance_name)
        pysensu_yelp_send_event_patch.assert_called_once_with(fake_check_name, fake_runbook, fake_status,
                                                              fake_output, fake_team, **expected_kwargs)


def test_check_service_instance():
    fake_service_name = "fake_service"
    fake_instance_name = "fake_instance"
    fake_status = 42
    fake_output = "Check passed"
    fake_port = 666
    expected_check_name = 'soa_fake_service.fake_instance_http_frontends'
    with contextlib.nested(
         mock.patch("service_deployment_tools.marathon_tools.get_proxy_port_for_instance",
                    return_value=fake_port),
         mock.patch("check_marathon_services_http_frontends.send_event"),
         mock.patch("check_marathon_services_http_frontends.check_http", return_value=(fake_status, fake_output))
    ) as (
         get_proxy_port_patch,
         send_event_patch,
         check_http_patch
    ):
        check_marathon_services_http_frontends.check_service_instance(fake_service_name, fake_instance_name)
        get_proxy_port_patch.assert_called_once_with(fake_service_name, fake_instance_name)
        check_http_patch.assert_called_once_with(fake_port)
        send_event_patch.assert_called_once_with(fake_service_name, fake_instance_name,
                                                 expected_check_name, fake_status, fake_output)


def test_MarathonServicesHttpFrontends_run():
    fake_service_list = [('fake_service1', 'fake_instance1'), ('fake_service2', 'fake_instance2')]
    expected_output_string = "Finished checking all services: fake_service1.fake_instance1 fake_service2.fake_instance2"
    with contextlib.nested(
         mock.patch("check_marathon_services_http_frontends.MarathonServicesHttpFrontends.__init__", return_value=None),
         mock.patch("check_marathon_services_http_frontends.MarathonServicesHttpFrontends.setup_logging", return_value=None),
         mock.patch("service_deployment_tools.marathon_tools.get_marathon_services_for_cluster",
                    return_value=fake_service_list),
         mock.patch("check_marathon_services_http_frontends.check_service_instance"),
    ) as (
         MarathonServicesHttpFrontends_patch,
         MarathonServicesHttpFrontends_logging_patch,
         get_marathon_services_for_cluster_patch,
         check_service_instance_patch
    ):
        fake_sensu_check = check_marathon_services_http_frontends.MarathonServicesHttpFrontends()
        fake_sensu_check.ok = mock.Mock()
        fake_sensu_check.run()

        MarathonServicesHttpFrontends_logging_patch.assert_called_once_with()
        get_marathon_services_for_cluster_patch.assert_called_once_with()
        assert check_service_instance_patch.call_count == len(fake_service_list)
        check_service_instance_patch.assert_any_call(fake_service_list[0][0], fake_service_list[0][1])
        check_service_instance_patch.assert_any_call(fake_service_list[1][0], fake_service_list[1][1])
        fake_sensu_check.ok.assert_called_once_with(expected_output_string)