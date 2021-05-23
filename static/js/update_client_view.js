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
            $(`#user_${id_to}_buttons`).html(response['buttons'])
            $(`#user_${id_to}_status`).text(response['status_text'])
            $(`#user_${id_to}_status`).css('color', response['status_style_color'])
        })
}

function set_unread_dialogs_count(n) {
    $('#message_count').text(n);
    $('#message_count').css('visibility', n ? 'visible' : 'hidden')
}

$(function () {
    let since = 0
    setInterval(function () {
        $.ajax('/notifications?since=' + since)
            .done(function (notifications) {
                for (let i = 0; i < notifications.length; i++) {
                    if (notifications[i].name === 'unread_messages')
                        set_unread_dialogs_count(notifications[i].data)
                    if (notifications[i].name === 'need_update_dialogs') {
                        if (document.location.href.split('/')[3] === 'dialogs') {
                            $('#dialogs').html(notifications[i].data)
                        }
                    }
                    since = notifications[i].timestamp
                }
            })
    }, 10000)
})

function set_time(id, time) {
    moment.locale("ru")
    let local_time = moment(time).subtract(new Date().getTimezoneOffset(), 'minutes').calendar()
    $(`#${id}`).text(' - ' + local_time)
}
