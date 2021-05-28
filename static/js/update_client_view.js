// Скрипт для динамического обновления контента на странице пользователя
function like_state(post_id, value) {
    // Функция меняет состояние лайка у поста
    $.post('/edit_post_rate', {
        id: post_id,
        value: value
    })
        .done(function (response) {
            if (response['is_like']) { // Изменение состояния лайка
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

            if (response['is_dislike']) { // Изменение состояния дизлайка
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
    // Функция изменяет внешний вид карточки пользователя
    $.post('/friendship_requests', {
        request_type: request_type,
        id_from: id_from,
        id_to: id_to
    })
        .done(function (response) {
            if (document.location.href.split('/')[3] !== 'add_friend_list') {
                // Удалить карточки со страницы с однотипными карточками (тк тип карточки меняется)
                $(`#user_${id_to}`).remove()
                if ($('#users_friendship_cards').children('div').length === 0) {
                    // Добавление блока об отсутствии информации, после удаления последнего блока
                    $('body').append(
                        '<div class="none">' +
                        '   <h1 style="color: black">Отсутствует информация по данной категории</h1>' +
                        '   <img src="../static/img/cat.png" alt="Грустный котик"/>' +
                        '</div>'
                    )
                }
                return
            }
            // Изменение кнопок и текста карточки
            $(`#user_${id_to}_buttons`).html(response['buttons'].join(''))
            $(`#user_${id_to}_status`).text(response['status_text'])
            $(`#user_${id_to}_status`).css('color', response['status_style_color'])
        })
}

function answer_offer(id_to, id_from) {
    // Функция для ответа на запрос дружбы
    $.post('/answer_offer', {
        user_from: id_from,
        user_to: id_to
    })
        .done(function (response) {
            // Изменение количество неотвеченных диалогов
            set_unanswered_offers_count('1', Number.parseInt($('#unanswered_subscribers_count1').text()) - 1)
            set_unanswered_offers_count('2', Number.parseInt($('#unanswered_subscribers_count2').text()) - 1)
            $(`#user_${id_from}_sub_btn`).remove() // Удаление кнопки "Оставить в подписчиках"
        })
}

function set_unread_dialogs_count(n) {
    // Функция устанавливает значение непрочитанных диалогов
    $('#dialogs_count').text(n);
    $('#dialogs_count').css('visibility', n ? 'visible' : 'hidden')
}

function set_unanswered_offers_count(id, n) {
    // Функция изменяет количество неотвеченных запросов дружбы
    $('#unanswered_subscribers_count' + id).text(n);
    $('#unanswered_subscribers_count' + id).css('visibility', Number.parseInt(n) ? 'visible' : 'hidden')
}

$(function () {
    // Подключение в WebSocket серверу
    let socket = io.connect('http://localhost:5000')
    let since = 0

    console.log(socket)
    socket.on('connect', function() { // Обработка подключения к сессии
        console.log('connect complete!')
    });

    socket.on('update', function (msg) { // Обработка всех уведомлений для пользователя
        console.log('receive message from server: "' + msg + '"')
        $.ajax('/notifications?since=' + since)
            .done(function (notifications) { // Получение всех уведомлений для пользователя
                for (let i = 0; i < notifications.length; i++) {
                    if (notifications[i].name === 'unread_messages') { // Обработка уведомления об изменении количества непрочитанных диалогов
                        console.log(notifications[i].data, 'aaa')
                        set_unread_dialogs_count(notifications[i].data)
                    }
                    if (notifications[i].name === 'new_friendship_request') { // Обработка уведомления о новом запросе дружбы
                        let data = notifications[i].data.split('+')

                        set_unanswered_offers_count('1', data[0])
                        set_unanswered_offers_count('2', data[0])

                        if (document.location.href.split('/')[3] === 'subscribers') {
                            $(`#user_${data[2]}`).remove()
                        }
                    }
                    if (notifications[i].name === 'need_update_dialogs') { // Обработка уведомления о необходимости обновить диалоги
                        if (document.location.href.split('/')[3] === 'dialogs') { // Изменение блока диалогов
                            $('#dialogs').html(notifications[i].data)
                        }
                    }
                    if (notifications[i].name === 'need_add_message') { // Обработка уведомления о добавлении сообщения
                        if (document.location.href.split('/')[3] === 'dialog') { // Добавление сообщение в диалог (на странице диалога между пользователями)
                            let data = notifications[i].data.split('+++')
                            $('#messages').append(data[2])
                            set_time(`time_${data[0]}`, data[1], 'LLL')

                            if (data.length === 4) { // Обновление прочитанных сообщений
                                $.post('/messages_read', {id: data[0], user: data[3]})
                                console.log(Number.parseInt($('#dialogs_count').text()) - 1, 'bbb')
                                set_unread_dialogs_count(Number.parseInt($('#dialogs_count').text()) - 1)
                            }
                        }
                    }
                    if (notifications[i].name === 'messages_read') { // Обработка уведомления о прочитанных сообщений
                        if (document.location.href.split('/')[3] === 'dialogs') { // Обновление прочитанного диалога (если пользователь на странице всех диалогов)
                            let data = notifications[i].data.split(',')
                            let ids = data[0].split(' ')
                            let target = $(`#${ids[0]}_${ids[1]}_dialog`).length ? $(`#${ids[0]}_${ids[1]}_dialog`) : $(`#${ids[1]}_${ids[0]}_dialog`)

                            $(target).text('Прочитано')
                            $(target).css('color', 'deepskyblue')
                            console.log($(target).text(), ids)
                        }
                        if (document.location.href.split('/')[3] === 'dialog') { // Обновление прочитанных сообщений в диалоге (если пользователь на странице диалога с пользователем)
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

    socket.on('error', function (msg) { // Обработка уведомлений об ошибках
        Notify.generate(msg, 'Ошибка!', 3)
    })

    socket.on('warning', function (msg) { // Обратка уведомлений о предупреждениях
        Notify.generate(msg, 'Внимание!', 2)
    })
})

function set_time(id, time, type='calendar') {
    // Функция устанавливает текущее время относительно сдвига от UTC с помощью moment-js
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
    // Функция динамически добавляет сообщение в диалог
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
