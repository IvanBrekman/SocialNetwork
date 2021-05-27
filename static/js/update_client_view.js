function like_state(post_id, value) {
    $.post('/edit_post_rate', {
        id: post_id,
        value: value
    })
        .done(function (response) {
            if (response['is_like']) {
                $(`#like_${post_id}`).removeClass('btn-outline-success')
                $(`#like_${post_id}`).addClass('btn-success')
                $(`#like_${post_id} span`).text('+' + response['likes'])
                $(`#like_${post_id} span`).css('color', 'black')
            } else {
                $(`#like_${post_id}`).removeClass('btn-success')
                $(`#like_${post_id}`).addClass('btn-outline-success')
                $(`#like_${post_id} span`).text('+' + response['likes'])
                $(`#like_${post_id} span`).css('color', 'green')
            }

            if (response['is_dislike']) {
                $(`#dislike_${post_id}`).removeClass('btn-outline-danger')
                $(`#dislike_${post_id}`).addClass('btn-danger')
                $(`#dislike_${post_id} span`).text('-' + response['dislikes'])
                $(`#dislike_${post_id} span`).css('color', 'black')
            } else {
                $(`#dislike_${post_id}`).removeClass('btn-danger')
                $(`#dislike_${post_id}`).addClass('btn-outline-danger')
                $(`#dislike_${post_id} span`).text('-' + response['dislikes'])
                $(`#dislike_${post_id} span`).css('color', 'red')
            }

        })
}

function card_type(request_type, id_from, id_to) {
    $.post('/friendship_requests', {
        request_type: request_type,
        id_from: id_from,
        id_to: id_to
    })
        .done(function (response) {
            if (document.location.href.split('/')[3] !== 'add_friend_list') {
                $(`#user_${id_to}`).remove()
                if ($('#users_friendship_cards').children('div').length === 0) {
                    $('body').append(
                        '<div class="none">' +
                        '   <h1 style="color: black">Отсутствует информация по данной категории</h1>' +
                        '   <img src="../static/img/cat.png" alt="Грустный котик"/>' +
                        '</div>'
                    )
                }
                return
            }
            $(`#user_${id_to}_buttons`).html(response['buttons'].join(''))
            $(`#user_${id_to}_status`).text(response['status_text'])
            $(`#user_${id_to}_status`).css('color', response['status_style_color'])
        })
}

function answer_offer(id_to, id_from) {
    $.post('/answer_offer', {
        user_from: id_from,
        user_to: id_to
    })
        .done(function (response) {
            set_unanswered_offers_count('1', Number.parseInt($('#unanswered_subscribers_count1').text()) - 1)
            set_unanswered_offers_count('2', Number.parseInt($('#unanswered_subscribers_count2').text()) - 1)
            $(`#user_${id_from}_sub_btn`).remove()
        })
}

function set_unread_dialogs_count(n) {
    $('#dialogs_count').text(n);
    $('#dialogs_count').css('visibility', n ? 'visible' : 'hidden')
}

function set_unanswered_offers_count(id, n) {
    $('#unanswered_subscribers_count' + id).text(n);
    $('#unanswered_subscribers_count' + id).css('visibility', Number.parseInt(n) ? 'visible' : 'hidden')
}

$(function () {
    let socket = io.connect('http://localhost:5000')
    let since = 0

    console.log(socket)
    socket.on('connect', function() {
        console.log('connect complete!')
    });

    socket.on('update', function (msg) {
        console.log('receive message from server: "' + msg + '"')
        $.ajax('/notifications?since=' + since)
            .done(function (notifications) {
                for (let i = 0; i < notifications.length; i++)
                    console.log(notifications[i].name, notifications[i].data)
                for (let i = 0; i < notifications.length; i++) {
                    if (notifications[i].name === 'unread_messages') {
                        console.log(notifications[i].data, 'aaa')
                        set_unread_dialogs_count(notifications[i].data)
                    }
                    if (notifications[i].name === 'new_friendship_request') {
                        let data = notifications[i].data.split('+')

                        set_unanswered_offers_count('1', data[0])
                        set_unanswered_offers_count('2', data[0])

                        if (document.location.href.split('/')[3] === 'subscribers') {
                            $(`#user_${data[2]}`).remove()
                        }
                    }
                    if (notifications[i].name === 'need_update_dialogs') {
                        if (document.location.href.split('/')[3] === 'dialogs') {
                            $('#dialogs').html(notifications[i].data)
                        }
                    }
                    if (notifications[i].name === 'need_add_message') {
                        if (document.location.href.split('/')[3] === 'dialog') {
                            let data = notifications[i].data.split('+++')
                            $('#messages').append(data[2])
                            set_time(`time_${data[0]}`, data[1], 'LLL')

                            if (data.length === 4) {
                                $.post('/messages_read', {id: data[0], user: data[3]})
                                console.log(Number.parseInt($('#dialogs_count').text()) - 1, 'bbb')
                                set_unread_dialogs_count(Number.parseInt($('#dialogs_count').text()) - 1)
                            }
                        }
                    }
                    if (notifications[i].name === 'messages_read') {
                        if (document.location.href.split('/')[3] === 'dialogs') {
                            let data = notifications[i].data.split(',')
                            let ids = data[0].split(' ')
                            let target = $(`#${ids[0]}_${ids[1]}_dialog`).length ? $(`#${ids[0]}_${ids[1]}_dialog`) : $(`#${ids[1]}_${ids[0]}_dialog`)

                            $(target).text('Прочитано')
                            $(target).css('color', 'deepskyblue')
                            console.log($(target).text(), ids)
                        }
                        if (document.location.href.split('/')[3] === 'dialog') {
                            let data = notifications[i].data.split(',')
                            let msg_ids = data[1].split(' ')
                            for (let id in msg_ids) {
                                $(`#message_text_${msg_ids[id]}`).remove()
                            }
                        }
                    }
                    since = notifications[i].timestamp
                }
            })
    })

    socket.on('error', function (msg) {
        Notify.generate(msg, 'Ошибка!', 3)
    })

    socket.on('warning', function (msg) {
        Notify.generate(msg, 'Внимание!', 2)
    })
})

function set_time(id, time, type='calendar') {
    moment.locale("ru")
    let local_time = null
    if (type === 'calendar')
        local_time = moment(time).subtract(new Date().getTimezoneOffset(), 'minutes').calendar()
    else if (type === 'LLL') {
        local_time = moment(time).subtract(new Date().getTimezoneOffset(), 'minutes').format('LLL')
    }
    $(`#${id}`).text(' - ' + local_time)
}

function append_message(dialog_id, id_from, id_to) {
    if (!$('#message_form').serialize().split('=')[1]) {
        $('#message').attr('placeholder', 'Введите сообщение')
        return
    }
    $.ajax({
        url: '/append_message',
        type: 'POST',
        data: {
            form: $('#message_form').serialize(),
            dialog: dialog_id,
            id_from: id_from,
            id_to: id_to
        },
        dataType: 'json',
        success: function (response) {
            $('#message_form')[0].reset()
        },
        error: function (response) {
            $('#messages').append('<span style="color: red">Ошибка! Не удалось отправить сообщение</span>')
        }
    })
}
